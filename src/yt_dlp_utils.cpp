#include "yt_dlp_utils.h"
#include <iostream>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <cstdlib>
#include <cstdio>
#include <ctime>
#include <algorithm>
#include <map>
#include <vector>

namespace fs = std::filesystem;
using namespace std;

namespace {

const std::string BEST_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best";

int runCommand(const std::string& command) {
    std::cout << "Executing: " << command << std::endl;
    return system(command.c_str());
}

// "hh:mm:ss", "mm:ss" or "ss" (decimals allowed) -> seconds, -1 if invalid
double parseTimeToSeconds(const std::string& text) {
    std::stringstream stream(text);
    std::string part;
    double total = 0;
    int parts = 0;
    while (std::getline(stream, part, ':')) {
        if (part.empty() || ++parts > 3) return -1;
        try {
            size_t used = 0;
            double value = std::stod(part, &used);
            if (used != part.size() || value < 0) return -1;
            total = total * 60 + value;
        } catch (...) {
            return -1;
        }
    }
    return parts > 0 ? total : -1;
}

// "HH:MM:SS,mmm" -> milliseconds
bool parseSrtTimestamp(const std::string& text, long long& ms) {
    int h, m, s, milli;
    char c1, c2, c3;
    std::istringstream in(text);
    if (!(in >> h >> c1 >> m >> c2 >> s >> c3 >> milli) || c1 != ':' || c2 != ':' || (c3 != ',' && c3 != '.')) {
        return false;
    }
    ms = ((h * 60LL + m) * 60 + s) * 1000 + milli;
    return true;
}

std::string formatSrtTimestamp(long long ms) {
    char buffer[32];
    snprintf(buffer, sizeof(buffer), "%02lld:%02lld:%02lld,%03lld",
             ms / 3600000, ms / 60000 % 60, ms / 1000 % 60, ms % 1000);
    return buffer;
}

// Keeps only the cues inside [startMs, endMs] and shifts them so that startMs becomes 0
// (yt-dlp --download-sections trims the video but not the subtitles)
bool trimSrt(const fs::path& input, const fs::path& output, long long startMs, long long endMs) {
    std::ifstream in(input, std::ios::binary);
    if (!in) return false;
    std::vector<std::vector<std::string>> blocks(1);
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.find_first_not_of(" \t") == std::string::npos) {
            if (!blocks.back().empty()) blocks.emplace_back();
        } else {
            blocks.back().push_back(line);
        }
    }

    std::ofstream out(output, std::ios::binary);
    if (!out) return false;
    int index = 0;
    for (const auto& block : blocks) {
        auto timing = std::find_if(block.begin(), block.end(),
                                   [](const std::string& l) { return l.find("-->") != std::string::npos; });
        if (timing == block.end() || timing + 1 == block.end()) continue;  // no timing or no text
        size_t arrow = timing->find("-->");
        long long cueStart, cueEnd;
        if (!parseSrtTimestamp(timing->substr(0, arrow), cueStart) ||
            !parseSrtTimestamp(timing->substr(arrow + 3), cueEnd)) continue;
        if (cueEnd <= startMs || cueStart >= endMs) continue;

        out << ++index << "\n"
            << formatSrtTimestamp(std::max(cueStart, startMs) - startMs) << " --> "
            << formatSrtTimestamp(std::min(cueEnd, endMs) - startMs) << "\n";
        for (auto text = timing + 1; text != block.end(); ++text) out << *text << "\n";
        out << "\n";
    }
    return true;
}

// Duration of a media file in seconds (ffprobe), -1 on error
double probeDurationSeconds(const fs::path& file) {
    const std::string command = "ffprobe -v error -show_entries format=duration -of csv=p=0 \"" + file.string() + "\"";
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) return -1;
    char buffer[64] = {0};
    const bool ok = fgets(buffer, sizeof(buffer), pipe) != nullptr;
    pclose(pipe);
    try {
        return ok ? std::stod(buffer) : -1;
    } catch (...) {
        return -1;
    }
}

// "it" / "en-orig" -> ISO 639-2 code used by mp4/mkv language tags
std::string toIso639_2(const std::string& lang) {
    static const std::map<std::string, std::string> codes = {
        {"ar", "ara"}, {"de", "deu"}, {"en", "eng"}, {"es", "spa"}, {"fr", "fra"}, {"hi", "hin"},
        {"it", "ita"}, {"ja", "jpn"}, {"ko", "kor"}, {"nl", "nld"}, {"pl", "pol"}, {"pt", "por"},
        {"ro", "ron"}, {"ru", "rus"}, {"sv", "swe"}, {"tr", "tur"}, {"uk", "ukr"}, {"zh", "zho"},
    };
    auto found = codes.find(lang.substr(0, lang.find('-')));
    return found != codes.end() ? found->second : lang;
}

// Hidden temporary folder in the current directory (same filesystem: rename always works)
fs::path createTmpDir() {
    const fs::path tmpDir = fs::current_path() / (".ytdlp_utility_tmp_" + std::to_string(std::time(nullptr)));
    fs::create_directories(tmpDir);
    return tmpDir;
}

// Trimmed download + subtitles: download clip and SRT in a temporary folder,
// cut/shift the SRT to the selection, mux everything with ffmpeg (no re-encoding)
void downloadTrimmedVideoWithSubtitles(const std::string& ytdlpCommand, double startSec, double endSec) {
    const fs::path tmpDir = createTmpDir();

    runCommand(ytdlpCommand + " -o \"" + (tmpDir / "%(title)s.%(ext)s").string() + "\"");

    fs::path video;
    std::vector<fs::path> subtitles;
    for (const auto& entry : fs::directory_iterator(tmpDir)) {
        const std::string ext = entry.path().extension().string();
        if (ext == ".srt") {
            subtitles.push_back(entry.path());
        } else if (ext != ".vtt" && ext != ".part" && ext != ".ytdl" &&
                   (video.empty() || fs::file_size(entry.path()) > fs::file_size(video))) {
            video = entry.path();
        }
    }
    std::sort(subtitles.begin(), subtitles.end());

    if (video.empty()) {
        std::cerr << "Video download failed, nothing to do." << std::endl;
        fs::remove_all(tmpDir);
        return;
    }

    const std::string ext = video.extension().string();
    const bool isMp4 = (ext == ".mp4" || ext == ".m4v" || ext == ".mov");
    const std::string outExt = (isMp4 || ext == ".mkv") ? ext : ".mkv";  // webm only supports WebVTT
    const fs::path finalPath = fs::current_path() / (video.stem().string() + outExt);

    if (subtitles.empty()) {
        std::cerr << "No subtitles downloaded, saving the video without subtitles." << std::endl;
        fs::rename(video, fs::current_path() / video.filename());
        fs::remove_all(tmpDir);
        return;
    }

    // safe names without the title (which may contain quotes or shell characters)
    const fs::path tmpVideo = tmpDir / ("video" + ext);
    const fs::path tmpOutput = tmpDir / ("output" + outExt);
    fs::rename(video, tmpVideo);

    // Without re-encoding the cut starts at the previous keyframe: mp4 hides that extra part
    // with an edit list, mkv/webm keep it. Real start = start - (file duration - requested duration)
    double prerollSec = 0;
    if (endSec > startSec) {
        const double fileSec = probeDurationSeconds(tmpVideo);
        if (fileSec > endSec - startSec) prerollSec = std::min(fileSec - (endSec - startSec), startSec);
    }
    if (prerollSec > 0.1) {
        std::cout << "Video starts " << prerollSec << "s before the selection (keyframe), subtitles aligned to it" << std::endl;
    }
    const long long startMs = static_cast<long long>((startSec - prerollSec) * 1000);
    const long long endMs = endSec < 0 ? (1LL << 62) : static_cast<long long>(endSec * 1000);

    std::string inputs = " -i \"" + tmpVideo.string() + "\"";
    std::string maps = " -map 0";
    std::string metadata;
    int count = 0;
    for (const auto& sub : subtitles) {
        const fs::path cut = tmpDir / ("sub" + std::to_string(count) + ".srt");
        if (!trimSrt(sub, cut, startMs, endMs)) continue;
        const std::string lang = sub.stem().extension().string().substr(1);  // "Title.it.srt" -> "it"
        const std::string idx = std::to_string(count);
        inputs += " -i \"" + cut.string() + "\"";
        maps += " -map " + std::to_string(count + 1);
        metadata += " -metadata:s:s:" + idx + " language=" + toIso639_2(lang) +
                    " -metadata:s:s:" + idx + " title=" + lang;
        ++count;
    }

    const std::string ffmpeg = "ffmpeg -v error -y" + inputs + maps + " -c copy -c:s " +
                               (isMp4 ? "mov_text" : "srt") + metadata + " \"" + tmpOutput.string() + "\"";
    if (runCommand(ffmpeg) == 0 && fs::exists(tmpOutput)) {
        fs::rename(tmpOutput, finalPath);
        std::cout << "Saved with " << count << " subtitle track(s): " << finalPath.filename().string() << std::endl;
    } else {
        std::cerr << "ffmpeg failed, saving the video without subtitles." << std::endl;
        fs::rename(tmpVideo, fs::current_path() / video.filename());
    }
    fs::remove_all(tmpDir);
}

}  // namespace

// VIDEO+AUDIO
// bestFormat: best mp4+m4a, otherwise interactive selection (-f-)
// startTime empty: full video, otherwise trimmed from startTime to endTime
// subLangs empty: no subtitles, otherwise those languages are embedded as subtitle tracks
void downloadVideo(const std::string& url, bool bestFormat, bool useCookies,
                   const std::string& startTime, const std::string& endTime, const std::string& subLangs) {
    std::string command = "yt-dlp";
    if (useCookies) command += " --cookies-from-browser firefox";
    command += bestFormat ? " -f \"" + BEST_FORMAT + "\"" : " -f-";
    command += " --verbose \"" + url + "\"";

    const bool trim = !startTime.empty();
    if (trim) command += " --download-sections \"*" + startTime + "-" + endTime + "\"";

    if (subLangs.empty()) {
        runCommand(command + " -o \"%(title)s.%(ext)s\"");
        return;
    }

    // EXPERIMENTAL
    // --ignore-errors: a subtitle that fails (e.g. HTTP 429) doesn't stop the video download
    // --write-subs + --write-auto-subs: manual subtitles preferred, auto-generated as fallback
    // --sub-format srt/best: native SRT (converting YouTube auto VTT duplicates every line)
    command += " --ignore-errors --write-subs --write-auto-subs --sub-langs \"" + subLangs +
               "\" --sub-format \"srt/best\" --convert-subs srt";

    if (!trim) {
        // with --write-subs yt-dlp keeps the subtitle files after embedding:
        // write them in a temporary folder, deleted at the end
        // webm only supports WebVTT subtitles: remux to mkv before embedding
        const fs::path tmpDir = createTmpDir();
        runCommand(command + " --embed-subs --remux-video \"webm>mkv\" -o \"%(title)s.%(ext)s\" -o \"subtitle:" +
                   (tmpDir / "%(title)s.%(ext)s").string() + "\"");
        fs::remove_all(tmpDir);
        return;
    }

    const double startSec = parseTimeToSeconds(startTime);
    const double endSec = parseTimeToSeconds(endTime);  // -1 (e.g. "inf") = until the end
    if (startSec < 0) {
        std::cerr << "Invalid start time, cannot align subtitles." << std::endl;
        return;
    }
    downloadTrimmedVideoWithSubtitles(command, startSec, endSec);
}

// AUDIO MP3 WITH THUMBNAIL
void downloadAudioMp3WithThumbnail(const std::string& url) {
    std::string command = "yt-dlp -x --embed-thumbnail --audio-format mp3 -o \"%(title)s.%(ext)s\" --verbose " + url;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// create a directory with the name of the playlist
std::string createPlaylistDirectory(const std::string& url) {
    std::string getPlaylistNameCmd = "yt-dlp --flat-playlist --playlist-end 1 --print \"%(playlist_title)s\" \"" + url + "\" ";
    std::string playlistName = "";
    
    FILE* pipe = popen(getPlaylistNameCmd.c_str(), "r");
    if (!pipe) {
        std::cerr << "Error getting playlist name !" << std::endl;
        return "Playlist";
    }
    
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
        playlistName += buffer;
    }
    pclose(pipe);

    playlistName.erase(playlistName.find_last_not_of("\n\r") + 1);

    if (playlistName.empty()) {
        playlistName = "Playlist";
    }

    if (!fs::exists(playlistName)) {
        fs::create_directory(playlistName);
    }

    return playlistName;
}

// PLAYLIST AUDIO MP3 WITH THUMBNAIL AND ENUMERATION
void downloadPlaylistAudioMp3WithThumbnailAndEnumeration(const std::string& url) {   
    string playlistDir = createPlaylistDirectory(url);
    std::string command = 
        "yt-dlp -f ba -x --audio-format mp3 --embed-thumbnail "
        "-o \"" + playlistDir + "/%(playlist_index)s-%(title)s.%(ext)s\" "
        "--yes-playlist \"" + url + "\"";
    
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// PLAYLIST AUDIO MP3 WITH THUMBNAIL
void downloadPlaylistAudioMp3WithThumbnail(const std::string& url) {
    string playlistDir = createPlaylistDirectory(url);
    std::string command = 
        "yt-dlp -f ba -x --audio-format mp3 --embed-thumbnail "
        "-o \"" + playlistDir + "/%(title)s.%(ext)s\" "
        "--yes-playlist \"" + url + "\"";
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}


// PLAYLIST VIDEO+AUDIO MP4+M4A BEST
void downloadPlaylistBestVideoAudio(const std::string& url) {
    string playlistDir = createPlaylistDirectory(url);
    std::string command = 
        "yt-dlp -f \"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best\" "
        "-o \"" + playlistDir + "/%(title)s.%(ext)s\" "
        "--yes-playlist \"" + url + "\"";
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// PLAYLIST VIDEO+AUDIO MP4+M4A BEST ENUMERATION
void downloadPlaylistBestVideoAudioWithEnumeration(const std::string& url) {
    string playlistDir = createPlaylistDirectory(url);
    std::string command = 
        "yt-dlp -f \"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best\" "
        "-o \"" + playlistDir + "/%(playlist_index)s-%(title)s.%(ext)s\" "
        "--yes-playlist \"" + url + "\"";
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// SUBTITLES (manual + auto-generated)
// languages empty -> all manual subtitles + auto-generated captions in the original language
// languages set   -> only those languages (manual preferred, auto-generated as fallback)
// --ignore-errors: a language that fails (e.g. HTTP 429) doesn't stop the others
// --sub-format srt/best: native SRT from the site; converting YouTube's roll-up VTT
// auto-captions duplicates every line, so --convert-subs is only a fallback
void downloadSubtitles(const std::string& url, const std::string& languages, bool useCookies) {
    const std::string base = useCookies ? "yt-dlp --cookies-from-browser firefox" : "yt-dlp";
    const std::string common = " --ignore-errors --skip-download --sub-format \"srt/best\" --convert-subs srt -o \"%(title)s.%(ext)s\" \"" + url + "\"";
    std::vector<std::string> commands;
    if (languages.empty()) {
        // "all" with --write-auto-subs would also fetch ~150 auto-translations (HTTP 429),
        // so manual subs and original auto captions are fetched separately
        commands.push_back(base + " --write-subs --sub-langs \"all,-live_chat\"" + common);
        commands.push_back(base + " --write-auto-subs --sub-langs \".*-orig\"" + common);
    } else {
        commands.push_back(base + " --write-subs --write-auto-subs --sub-langs \"" + languages + "\"" + common);
    }
    for (const auto& command : commands) {
        std::cout << "Executing: " << command << std::endl;
        system(command.c_str());
    }
}