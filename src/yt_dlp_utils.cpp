#include "yt_dlp_utils.h"
#include <iostream>
#include <filesystem>
#include <cstdlib>

namespace fs = std::filesystem;
using namespace std;

// VIDEO+AUDIO COOKIES
void downloadFullVideoWithCookies(const std::string& url) {
    std::string command = "yt-dlp --cookies-from-browser firefox -f- -o \"%(title)s.%(ext)s\" --verbose " + url;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}
// VIDEO+AUDIO BEST COOKIES
void downloadFullVideoWithCookiesBest(const std::string& url) {
    std::string command = "yt-dlp --cookies-from-browser firefox -f \"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best\" -o \"%(title)s.%(ext)s\" --verbose " + url;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// VIDEO+AUDIO
void downloadFullVideoWithoutCookies(const std::string& url) {
    std::string command = "yt-dlp -f- -o \"%(title)s.%(ext)s\" --verbose " + url;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}
// VIDEO+AUDIO BEST
void downloadFullVideoWithoutCookiesBest(const std::string& url) {
    std::string command = "yt-dlp -f \"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best\" -o \"%(title)s.%(ext)s\" --verbose " + url;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// TRIMMED_VIDEO+AUDIO+COOKIES
void downloadTrimmedVideoWithCookies(const std::string& url, const std::string& selectionString) {
    std::string command = "yt-dlp --cookies-from-browser firefox -f- -o \"%(title)s.%(ext)s\" --verbose " + url + " --download-sections " + selectionString;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// TRIMMED_VIDEO+AUDIO BEST COOKIES
void downloadTrimmedVideoWithCookiesBest(const std::string& url, const std::string& selectionString) {
    std::string command = "yt-dlp --cookies-from-browser firefox -f \"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best\" -o \"%(title)s.%(ext)s\" --verbose " + url + " --download-sections " + selectionString;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// TRIMMED_VIDEO+AUDIO
void downloadTrimmedVideoWithoutCookies(const std::string& url, const std::string& selectionString) {
    std::string command = "yt-dlp -f- -o \"%(title)s.%(ext)s\" --verbose " + url + " --download-sections " + selectionString;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}

// TRIMMED_VIDEO+AUDIO BEST
void downloadTrimmedVideoWithoutCookiesBest(const std::string& url, const std::string& selectionString) {
    std::string command = "yt-dlp -f \"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best\" -o \"%(title)s.%(ext)s\" --verbose " + url + " --download-sections " + selectionString;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
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

void downloadSubtitles(const std::string& url) {
    std::string command = "yt-dlp --all-subs --skip-download --convert-subs=srt -o \"%(title)s.%(ext)s\" " + url;
    std::cout << "Executing: " << command << std::endl;
    system(command.c_str());
}