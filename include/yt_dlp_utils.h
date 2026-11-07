#ifndef YT_DLP_UTILS_H
#define YT_DLP_UTILS_H

#include <string>


void downloadVideo(const std::string& url, bool bestFormat, bool useCookies,
                   const std::string& startTime, const std::string& endTime, const std::string& subLangs);
void downloadAudioMp3WithThumbnail(const std::string& url);
void downloadPlaylistAudioMp3WithThumbnailAndEnumeration(const std::string& url);
void downloadPlaylistAudioMp3WithThumbnail(const std::string& url);
void downloadPlaylistBestVideoAudio(const std::string& url);
void downloadPlaylistBestVideoAudioWithEnumeration(const std::string& url);
void downloadSubtitles(const std::string& url, const std::string& languages, bool useCookies);
std::string createPlaylistDirectory(const std::string& url);

#endif
