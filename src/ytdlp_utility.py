import subprocess
import sys
import os
import re

# Colori per il terminale
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"

def verify_install(program):
    if os.name == 'nt':  # Windows
        cmd = f"where {program}"
        with open(os.devnull, 'w') as devnull:
            return subprocess.call(cmd, shell=True, stdout=devnull, stderr=devnull) == 0
    else:  # Linux/Unix/Mac
        cmd = f"which {program}"
        with open(os.devnull, 'w') as devnull:
            return subprocess.call(cmd, shell=True, stdout=devnull, stderr=devnull) == 0

def pause_application():
    if os.name == 'nt':  # Windows
        os.system("pause")
    else:  # Linux/Unix/Mac
        input("Premi INVIO per continuare...")

def get_user_input(prompt):
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print(f"\n{RED}Operazione annullata dall'utente{RESET}")
        sys.exit(0)

def execute_command(command):
    print(f"Executing: {command}")
    os.system(command)

def create_playlist_directory(url):
    """Crea una directory con il nome della playlist"""
    get_playlist_name_cmd = f'yt-dlp --flat-playlist --playlist-end 1 --print "%(playlist_title)s" "{url}"'
    
    try:
        result = subprocess.run(get_playlist_name_cmd, shell=True, capture_output=True, text=True)
        playlist_name = result.stdout.strip()
        
        # Rimuovi caratteri non validi per i nomi di file
        playlist_name = re.sub(r'[<>:"/\\|?*]', '', playlist_name)
        
        if not playlist_name:
            playlist_name = "Playlist"
        
        if not os.path.exists(playlist_name):
            os.makedirs(playlist_name)
        
        return playlist_name
    except Exception as e:
        print(f"Error getting playlist name: {e}")
        playlist_name = "Playlist"
        if not os.path.exists(playlist_name):
            os.makedirs(playlist_name)
        return playlist_name

##* ytdlp CALlS

# VIDEO+AUDIO COOKIES
def download_full_video_with_cookies(url):
    command = f'yt-dlp --cookies-from-browser firefox -f- -o "%(title)s.%(ext)s" --verbose "{url}"'
    execute_command(command)

# VIDEO+AUDIO BEST COOKIES
def download_full_video_with_cookies_best(url):
    command = f'yt-dlp --cookies-from-browser firefox -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o "%(title)s.%(ext)s" --verbose "{url}"'
    execute_command(command)

# VIDEO+AUDIO
def download_full_video_without_cookies(url):
    command = f'yt-dlp -f- -o "%(title)s.%(ext)s" --verbose "{url}"'
    execute_command(command)

# VIDEO+AUDIO BEST
def download_full_video_without_cookies_best(url):
    command = f'yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o "%(title)s.%(ext)s" --verbose "{url}"'
    execute_command(command)

# TRIMMED_VIDEO+AUDIO+COOKIES
def download_trimmed_video_with_cookies(url, selection_string):
    command = f'yt-dlp --cookies-from-browser firefox -f- -o "%(title)s.%(ext)s" --verbose "{url}" --download-sections "{selection_string}"'
    execute_command(command)

# TRIMMED_VIDEO+AUDIO BEST COOKIES
def download_trimmed_video_with_cookies_best(url, selection_string):
    command = f'yt-dlp --cookies-from-browser firefox -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o "%(title)s.%(ext)s" --verbose "{url}" --download-sections "{selection_string}"'
    execute_command(command)

# TRIMMED_VIDEO+AUDIO
def download_trimmed_video_without_cookies(url, selection_string):
    command = f'yt-dlp -f- -o "%(title)s.%(ext)s" --verbose "{url}" --download-sections "{selection_string}"'
    execute_command(command)

# TRIMMED_VIDEO+AUDIO BEST
def download_trimmed_video_without_cookies_best(url, selection_string):
    command = f'yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o "%(title)s.%(ext)s" --verbose "{url}" --download-sections "{selection_string}"'
    execute_command(command)

# AUDIO MP3 WITH THUMBNAIL
def download_audio_mp3_with_thumbnail(url):
    command = f'yt-dlp -x --embed-thumbnail --audio-format mp3 -o "%(title)s.%(ext)s" --verbose "{url}"'
    execute_command(command)

# PLAYLIST AUDIO MP3 WITH THUMBNAIL AND ENUMERATION
def download_playlist_audio_mp3_with_thumbnail_and_enumeration(url):
    playlist_dir = create_playlist_directory(url)
    command = f'yt-dlp -f ba -x --audio-format mp3 --embed-thumbnail -o "{playlist_dir}/%(playlist_index)s-%(title)s.%(ext)s" --yes-playlist "{url}"'
    execute_command(command)

# PLAYLIST AUDIO MP3 WITH THUMBNAIL
def download_playlist_audio_mp3_with_thumbnail(url):
    playlist_dir = create_playlist_directory(url)
    command = f'yt-dlp -f ba -x --audio-format mp3 --embed-thumbnail -o "{playlist_dir}/%(title)s.%(ext)s" --yes-playlist "{url}"'
    execute_command(command)

# PLAYLIST VIDEO+AUDIO MP4+M4A BEST
def download_playlist_best_video_audio(url):
    playlist_dir = create_playlist_directory(url)
    command = f'yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o "{playlist_dir}/%(title)s.%(ext)s" --yes-playlist "{url}"'
    execute_command(command)

# PLAYLIST VIDEO+AUDIO MP4+M4A BEST ENUMERATION
def download_playlist_best_video_audio_with_enumeration(url):
    playlist_dir = create_playlist_directory(url)
    command = f'yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o "{playlist_dir}/%(playlist_index)s-%(title)s.%(ext)s" --yes-playlist "{url}"'
    execute_command(command)

# DOWNLOAD SUBTITLES
def download_subtitles(url):
    command = f'yt-dlp --all-subs --skip-download --convert-subs=srt -o "%(title)s.%(ext)s" "{url}"'
    execute_command(command)

##* ytdlp CALlS

def handle_video_audio_mode_with_selection():
    """Modalità Video+Audio con selezione"""
    print("Video+Audio with Selection mode selected")
    
    # URL
    url = get_user_input("Enter the URL: ")
    
    # USE OF COOKIES
    cookies_flag = False
    choice = get_user_input("Do you want to use cookies? (y/n): ").lower()
    if choice == 'y':
        cookies_flag = True
    elif choice == 'n':
        cookies_flag = False
    else:
        print("Invalid choice")
        return 1
    
    # TRIM FUNCTION
    trim_flag = False
    selection_string = ""
    choice = get_user_input("Do you want to trim the video? (y/n): ").lower()
    if choice == 'y':
        trim_flag = True
        start_time = get_user_input("Enter the start time (hh:mm:ss OR mm:ss): ")
        end_time = get_user_input("Enter the end time (hh:mm:ss OR mm:ss): ")
        selection_string = f"*{start_time}-{end_time}"
        print(f"Your selection: {selection_string}")
    elif choice == 'n':
        trim_flag = False
    else:
        print("Invalid choice")
        return 1
    
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    print(f"{RED}USE id+id FOR SELECTION{RESET}")
    print(f"{RED}----------------------------------------------------{RESET}")
    
    if cookies_flag and trim_flag:
        download_trimmed_video_with_cookies(url, selection_string)
    elif not cookies_flag and trim_flag:
        download_trimmed_video_without_cookies(url, selection_string)
    elif cookies_flag and not trim_flag:
        download_full_video_with_cookies(url)
    elif not cookies_flag and not trim_flag:
        download_full_video_without_cookies(url)
    
    return 0

def handle_video_audio_mode_with_best_format():
    """Modalità Video+Audio con formato migliore"""
    print("Best MP4+M4A mode selected")
    
    # URL
    url = get_user_input("Enter the URL: ")
    
    # USE OF COOKIES
    cookies_flag = False
    choice = get_user_input("Do you want to use cookies? (y/n): ").lower()
    if choice == 'y':
        cookies_flag = True
    elif choice == 'n':
        cookies_flag = False
    else:
        print("Invalid choice")
        return 1
    
    # TRIM FUNCTION
    trim_flag = False
    selection_string = ""
    choice = get_user_input("Do you want to trim the video? (y/n): ").lower()
    if choice == 'y':
        trim_flag = True
        start_time = get_user_input("Enter the start time (hh:mm:ss OR mm:ss): ")
        end_time = get_user_input("Enter the end time (hh:mm:ss OR mm:ss): ")
        selection_string = f"*{start_time}-{end_time}"
        print(f"Your selection: {selection_string}")
    elif choice == 'n':
        trim_flag = False
    else:
        print("Invalid choice")
        return 1
    
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    print(f"{RED}----------------------------------------------------{RESET}")
    
    if cookies_flag and trim_flag:
        download_trimmed_video_with_cookies_best(url, selection_string)
    elif not cookies_flag and trim_flag:
        download_trimmed_video_without_cookies_best(url, selection_string)
    elif cookies_flag and not trim_flag:
        download_full_video_with_cookies_best(url)
    elif not cookies_flag and not trim_flag:
        download_full_video_without_cookies_best(url)
    
    return 0

def handle_audio_mode():
    """Modalità solo audio"""
    print("Audio mode selected, download the mp3 format")
    url = get_user_input("Enter the URL: ")
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    print(f"{RED}----------------------------------------------------{RESET}")
    download_audio_mp3_with_thumbnail(url)
    return 0

def handle_playlist_mode():
    """Modalità playlist"""
    print("Playlist mode selected")
    url = get_user_input("Enter the URL: ")
    print("Enter format:")
    print("1) Audio mode (mp3) with enumeration (1-NameVideo1.mp3 2-NameVideo2.mp3...)")
    print("2) Audio mode (mp3) without enumeration")
    print("3) Video+Audio mode (best mp4+m4a) with enumeration (1-NameVideo1.mp4 2-NameVideo2.mp4...)")
    print("4) Video+Audio mode (best mp4+m4a) without enumeration")
    choice = get_user_input("Select number: ")
    
    try:
        choice = int(choice)
    except ValueError:
        print("Invalid choice")
        return 1
    
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    print(f"{RED}----------------------------------------------------{RESET}")
    
    if choice == 1:
        download_playlist_audio_mp3_with_thumbnail_and_enumeration(url)
    elif choice == 2:
        download_playlist_audio_mp3_with_thumbnail(url)
    elif choice == 3:
        download_playlist_best_video_audio_with_enumeration(url)
    elif choice == 4:
        download_playlist_best_video_audio(url)
    else:
        print("Invalid choice")
        return 1
    
    return 0

def handle_subtitles_mode():
    """Modalità sottotitoli"""
    print("Subtitles mode selected")
    url = get_user_input("Enter the URL: ")
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    print(f"{RED}----------------------------------------------------{RESET}")
    download_subtitles(url)
    return 0

def help_menu():
    """Mostra il menu di aiuto"""
    print("Usage: ytdlp_utility [options]")
    print("Options:")
    print("  (no options)  Start Video+Audio with full selection of the output format")
    print("  -h or --help  Show this help message and exit")
    print("  --best           Download the best Mp4+m4a available format")
    print("  -a           Download only the mp3 format")
    print("  -p           Enter playlist mode")
    print("  --sub       Download all subtitles available (not auto generated)")

def main():
    # Verifica installazioni
    if not verify_install("yt-dlp"):
        print("yt-dlp is not installed!")
        return 1
    
    if not verify_install("ffmpeg"):
        print("ffmpeg is not installed!")
        return 1
    
    # Gestione argomenti
    if len(sys.argv) == 1:
        result = handle_video_audio_mode_with_selection()
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg in ["-h", "--help"]:
            help_menu()
            return 0
        elif arg == "--best":
            result = handle_video_audio_mode_with_best_format()
        elif arg == "-a":
            result = handle_audio_mode()
        elif arg == "-p":
            result = handle_playlist_mode()
        elif arg == "--sub":
            result = handle_subtitles_mode()
        else:
            print("Invalid argument")
            return 1
    else:
        print("Too many arguments")
        return 1
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        return 0
    
    print(f"{GREEN}----------------------------------------------------{RESET}")
    print(f"{GREEN}END YT-DLP UTILITY EXECUTION...{RESET}")
    pause_application()
    return result

if __name__ == "__main__":
    sys.exit(main())