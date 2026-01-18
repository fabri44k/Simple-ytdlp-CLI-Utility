#include <iostream>
#include "../include/yt_dlp_utils.h"

using namespace std;

#define RESET   "\033[0m"
#define RED     "\033[31m"
#define GREEN   "\033[32m"






bool verify_install(const string& program) {
#ifdef _WIN32 // Windows
    string command = "where " + program + " >nul 2>&1";
#else // Linux/Unix/Mac
    string command = "which " + program + " >/dev/null 2>&1";
#endif
    return system(command.c_str()) == 0;
}


int  handleVideoAudioModeWithSelection(){
    cout << "Video+Audio with Selection mode selected" << endl;
    // URL 
    string URL;
    cout << "Enter the URL: ";
    cin >> URL;

    // USE OF COOKIES
    bool cookies_flag = false;
    cout << "Do you want to use cookies? (y/n): ";
    char choice;
    cin >> choice;
    if (choice == 'y') {
        cookies_flag = true;
    } else if (choice == 'n') {
        cookies_flag = false;
    } else {
        cout << "Invalid choice" << endl;
        return 1;
    }
    
    // TRIM FUNCTION
    bool trim_flag = false;
    string selection_string;
    cout << "Do you want to trim the video? (y/n): ";
    cin >> choice;
    if (choice == 'y') {
        trim_flag = true;
        string start_time, end_time;
        cout << "Enter the start time (hh:mm:ss OR mm:ss): ";
        cin >> start_time;
        cout << "Enter the end time (hh:mm:ss OR mm:ss): ";
        cin >> end_time;
        selection_string = "*"+start_time+"-"+end_time;
        cout << "Your selection: "<< selection_string << endl;

    } else if (choice == 'n') {
        trim_flag = false;
    } else {
        cout << "Invalid choice" << endl;
        return 1;
    }
    
    cout << RED << "\nSTART YT-DLP DOWNLOAD..." << RESET << endl;
    cout << RED << "USE id+id FOR SELECTION" << RESET << endl;
    cout << RED << "----------------------------------------------------" << RESET << endl;
    if (cookies_flag && trim_flag) {
        downloadTrimmedVideoWithCookies(URL, selection_string);
    } else if (!cookies_flag && trim_flag) {
        downloadTrimmedVideoWithoutCookies(URL, selection_string);
    } else if (cookies_flag && !trim_flag) {
        downloadFullVideoWithCookies(URL);
    } else if (!cookies_flag && !trim_flag) {
        downloadFullVideoWithoutCookies(URL);
    }

    return 0;
    
}

int handleVideoAudioModeWithBestFormat(){
    cout << "Best MP4+M4A mode selected" << endl;
    // URL 
    string URL;
    cout << "Enter the URL: ";
    cin >> URL;

    // USE OF COOKIES
    bool cookies_flag = false;
    cout << "Do you want to use cookies? (y/n): ";
    char choice;
    cin >> choice;
    if (choice == 'y') {
        cookies_flag = true;
    } else if (choice == 'n') {
        cookies_flag = false;
    } else {
        cout << "Invalid choice" << endl;
        return 1;
    }
    
    // TRIM FUNCTION
    bool trim_flag = false;
    string selection_string;
    cout << "Do you want to trim the video? (y/n): ";
    cin >> choice;
    if (choice == 'y') {
        trim_flag = true;
        string start_time, end_time;
        cout << "Enter the start time (hh:mm:ss OR mm:ss): ";
        cin >> start_time;
        cout << "Enter the end time (hh:mm:ss OR mm:ss): ";
        cin >> end_time;
        selection_string = "*"+start_time+"-"+end_time;
        cout << "Your selection: "<< selection_string << endl;

    } else if (choice == 'n') {
        trim_flag = false;
    } else {
        cout << "Invalid choice" << endl;
        return 1;
    }

    cout << RED << "\nSTART YT-DLP DOWNLOAD..." << RESET << endl;
    cout << RED << "----------------------------------------------------" << RESET << endl;
    if (cookies_flag && trim_flag) {
        downloadTrimmedVideoWithCookiesBest(URL, selection_string);
    } else if (!cookies_flag && trim_flag) {
        downloadTrimmedVideoWithoutCookiesBest(URL, selection_string);
    } else if (cookies_flag && !trim_flag) {
        downloadFullVideoWithCookiesBest(URL);
    } else if (!cookies_flag && !trim_flag) {
        downloadFullVideoWithoutCookiesBest(URL);
    }

    return 0;
}


int handleAudioMode(){
    cout << "Audio mode selected, download the mp3 format" << endl; 
    string URL;
    cout << "Enter the URL: ";
    cin >> URL;
    cout << RED << "\nSTART YT-DLP DOWNLOAD..." << RESET << endl;
    cout << RED << "----------------------------------------------------" << RESET << endl;
    downloadAudioMp3WithThumbnail(URL);
    return 0;
}

int handlePlaylistMode(){
    cout << "Playlist mode selected" << endl; 
    string URL;
    cout << "Enter the URL: ";
    cin >> URL;
    cout << "Enter format: " << endl;
    cout << "1) Audio mode (mp3) with enumeration (1-NameVideo1.mp3 2-NameVideo2.mp3...)" << endl;
    cout << "2) Audio mode (mp3) without enumeration" << endl;
    cout << "3) Video+Audio mode (best mp4+m4a) with enumeration (1-NameVideo1.mp4 2-NameVideo2.mp4...)" << endl;
    cout << "4) Video+Audio mode (best mp4+m4a) without enumeration" << endl;
    cout << "Select number: ";
    int choice;
    cin >> choice;
    
    cout << RED << "\nSTART YT-DLP DOWNLOAD..." << RESET << endl;
    cout << RED << "----------------------------------------------------" << RESET << endl;
 
    if (choice == 1) {
        downloadPlaylistAudioMp3WithThumbnailAndEnumeration(URL);
    } else if (choice == 2) {
        downloadPlaylistAudioMp3WithThumbnail(URL);
    } else if (choice == 3) {
        downloadPlaylistBestVideoAudioWithEnumeration(URL);
    } else if (choice == 4) {
        downloadPlaylistBestVideoAudio(URL);
    }
 
    else {
        cout << "Invalid choice" << endl;
        return 1;
    }

    return 0;
}

int handleSubtitlesMode() {
    cout << "Subtitles mode selected" << endl;
    string URL;
    cout << "Enter the URL: ";
    cin >> URL;

    cout << RED << "\nSTART YT-DLP DOWNLOAD..." << RESET << endl;
    cout << RED << "----------------------------------------------------" << RESET << endl;

    downloadSubtitles(URL);

    return 0;
}



void pauseApplication() {
#ifdef _WIN32 // Windows
    system("pause");
#else // Linux/Unix/Mac
    system("read -p \"Premi INVIO per continuare...\"");
#endif
}

void helpMenu(){
    cout << "Usage: ytdlp_utility [options]" << endl;
    cout << "Options:" << endl;
    cout << "  (no options)  Start Video+Audio with full selection of the output format" << endl;
    cout << "  -h or --help  Show this help message and exit" << endl;
    cout << "  --best           Download the best Mp4+m4a available format" << endl;
    cout << "  -a           Download only the mp3 format" << endl;
    cout << "  -p           Enter playlist mode" << endl;
    cout << "  --sub       Download all subtitles available (not auto generated)" << endl;
}





int main(int argc, char* argv[]) {

    if (!verify_install("yt-dlp")) {
        cout << "yt-dlp is not installed !" << endl;
        return 1;
    }

    if (!verify_install("ffmpeg")) {
        cout << "ffmpeg is not installed !" << endl;
        return 1;
    }

    // nessun parametro
    if (argc == 1) {
        handleVideoAudioModeWithSelection();
    } else if (argc == 2) {
        string arg = argv[1];
        if (arg == "-h" || arg == "--help") {
            helpMenu();
        } else if (arg == "--best") {
            handleVideoAudioModeWithBestFormat();
        } else if (arg == "-a") {
            handleAudioMode();
        } else if (arg == "-p") {
            handlePlaylistMode();
        } else if (arg == "--sub") {
            handleSubtitlesMode();
        }

        else {
            cout << "Invalid argument" << endl;
            return 1;
        }

    }
 
    cout << GREEN << "----------------------------------------------------" << RESET << endl;
    cout << GREEN << "END YT-DLP UTILITY EXECUTION..." << RESET << endl;
    pauseApplication();
    return 0;
}
