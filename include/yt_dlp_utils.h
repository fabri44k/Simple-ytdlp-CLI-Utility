#ifndef YT_DLP_UTILS_H
#define YT_DLP_UTILS_H

#include <string>


void downloadFullVideoWithCookies(const std::string& url);
void downloadFullVideoWithCookiesBest(const std::string& url);
void downloadFullVideoWithoutCookies(const std::string& url);
void downloadFullVideoWithoutCookiesBest(const std::string& url);
void downloadTrimmedVideoWithCookies(const std::string& url, const std::string& selectionString);
void downloadTrimmedVideoWithCookiesBest(const std::string& url, const std::string& selectionString);
void downloadTrimmedVideoWithoutCookies(const std::string& url, const std::string& selectionString);
void downloadTrimmedVideoWithoutCookiesBest(const std::string& url, const std::string& selectionString);
void downloadAudioMp3WithThumbnail(const std::string& url);
void downloadPlaylistAudioMp3WithThumbnailAndEnumeration(const std::string& url);
void downloadPlaylistAudioMp3WithThumbnail(const std::string& url);
void downloadPlaylistBestVideoAudio(const std::string& url);
void downloadPlaylistBestVideoAudioWithEnumeration(const std::string& url);
void downloadSubtitles(const std::string& url);
std::string createPlaylistDirectory(const std::string& url);

#endif
