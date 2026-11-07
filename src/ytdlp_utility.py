import subprocess
import sys
import os
import re
import shutil
import tempfile

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

BEST_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

ISO639_2 = {
    "ar": "ara", "de": "deu", "en": "eng", "es": "spa", "fr": "fra", "hi": "hin",
    "it": "ita", "ja": "jpn", "ko": "kor", "nl": "nld", "pl": "pol", "pt": "por",
    "ro": "ron", "ru": "rus", "sv": "swe", "tr": "tur", "uk": "ukr", "zh": "zho",
}

def parse_time_to_seconds(text):
    """"hh:mm:ss", "mm:ss" o "ss" (decimali ammessi) -> secondi, None se non valido"""
    parts = text.split(":")
    if not 1 <= len(parts) <= 3:
        return None
    total = 0.0
    for part in parts:
        try:
            value = float(part)
        except ValueError:
            return None
        if value < 0:
            return None
        total = total * 60 + value
    return total

SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")

def parse_srt_timestamp(text):
    m = SRT_TIME.search(text)
    if not m:
        return None
    h, mi, s, ms = map(int, m.groups())
    return ((h * 60 + mi) * 60 + s) * 1000 + ms

def format_srt_timestamp(ms):
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

def trim_srt(input_path, output_path, start_ms, end_ms):
    """Tiene solo le righe dentro [start_ms, end_ms] e le sposta in modo che start_ms diventi 0
    (yt-dlp --download-sections taglia il video ma non i sottotitoli)"""
    with open(input_path, encoding="utf-8", errors="replace") as f:
        blocks = re.split(r"\n[ \t]*\n", f.read().replace("\r\n", "\n"))
    out = []
    for block in blocks:
        lines = [l for l in block.split("\n") if l.strip()]
        timing = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if timing is None or timing + 1 >= len(lines):
            continue
        start_text, end_text = lines[timing].split("-->", 1)
        cue_start, cue_end = parse_srt_timestamp(start_text), parse_srt_timestamp(end_text)
        if cue_start is None or cue_end is None or cue_end <= start_ms or cue_start >= end_ms:
            continue
        out.append(f"{len(out) + 1}\n"
                   f"{format_srt_timestamp(max(cue_start, start_ms) - start_ms)} --> "
                   f"{format_srt_timestamp(min(cue_end, end_ms) - start_ms)}\n"
                   + "\n".join(lines[timing + 1:]) + "\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

def probe_duration_seconds(path):
    """Durata di un file multimediale in secondi (ffprobe), None se errore"""
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", path], capture_output=True, text=True)
        return float(result.stdout.strip())
    except (OSError, ValueError):
        return None

def download_trimmed_video_with_subtitles(ytdlp_command, start_sec, end_sec):
    """Trim + sottotitoli: scarica clip e SRT in una cartella temporanea, taglia/sposta gli SRT
    sulla selezione e unisce tutto con ffmpeg (senza ricodifica)"""
    tmp_dir = tempfile.mkdtemp(prefix=".ytdlp_utility_tmp_", dir=os.getcwd())
    try:
        execute_command(f'{ytdlp_command} -o "{os.path.join(tmp_dir, "%(title)s.%(ext)s")}"')

        subtitles = sorted(f for f in os.listdir(tmp_dir) if f.endswith(".srt"))
        videos = [f for f in os.listdir(tmp_dir) if os.path.splitext(f)[1] not in (".srt", ".vtt", ".part", ".ytdl")]
        if not videos:
            print("Video download failed, nothing to do.")
            return
        video = max(videos, key=lambda f: os.path.getsize(os.path.join(tmp_dir, f)))
        stem, ext = os.path.splitext(video)
        is_mp4 = ext in (".mp4", ".m4v", ".mov")
        out_ext = ext if is_mp4 or ext == ".mkv" else ".mkv"  # webm supporta solo WebVTT

        if not subtitles:
            print("No subtitles downloaded, saving the video without subtitles.")
            os.replace(os.path.join(tmp_dir, video), video)
            return

        # Senza ricodifica il taglio parte dal keyframe precedente: mp4 nasconde la parte in piu'
        # con una edit list, mkv/webm no. Inizio reale = inizio - (durata file - durata richiesta)
        video_path = os.path.join(tmp_dir, video)
        preroll = 0.0
        if end_sec is not None and end_sec > start_sec:
            file_sec = probe_duration_seconds(video_path)
            if file_sec is not None and file_sec > end_sec - start_sec:
                preroll = min(file_sec - (end_sec - start_sec), start_sec)
        if preroll > 0.1:
            print(f"Video starts {preroll:g}s before the selection (keyframe), subtitles aligned to it")
        start_ms = int((start_sec - preroll) * 1000)
        end_ms = int(end_sec * 1000) if end_sec is not None else 1 << 62

        # ffmpeg chiamato senza shell: il titolo puo' contenere qualsiasi carattere
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", video_path]
        maps, metadata = ["-map", "0"], []
        for i, sub in enumerate(subtitles):
            cut = os.path.join(tmp_dir, f"sub{i}.srt")
            trim_srt(os.path.join(tmp_dir, sub), cut, start_ms, end_ms)
            lang = os.path.splitext(os.path.splitext(sub)[0])[1][1:]  # "Title.it.srt" -> "it"
            cmd += ["-i", cut]
            maps += ["-map", str(i + 1)]
            metadata += [f"-metadata:s:s:{i}", f"language={ISO639_2.get(lang.split('-')[0], lang)}",
                         f"-metadata:s:s:{i}", f"title={lang}"]
        tmp_output = os.path.join(tmp_dir, "output" + out_ext)
        cmd += maps + ["-c", "copy", "-c:s", "mov_text" if is_mp4 else "srt"] + metadata + [tmp_output]
        print(f"Executing: {' '.join(cmd)}")
        if subprocess.call(cmd) == 0 and os.path.exists(tmp_output):
            os.replace(tmp_output, stem + out_ext)
            print(f"Saved with {len(subtitles)} subtitle track(s): {stem + out_ext}")
        else:
            print("ffmpeg failed, saving the video without subtitles.")
            os.replace(video_path, video)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

# VIDEO+AUDIO
# best_format: best mp4+m4a, altrimenti selezione interattiva (-f-)
# start_time vuoto: video intero, altrimenti tagliato da start_time a end_time
# sub_langs vuoto: nessun sottotitolo, altrimenti quelle lingue vengono aggiunte come tracce
def download_video(url, best_format, use_cookies, start_time="", end_time="", sub_langs=""):
    command = "yt-dlp"
    if use_cookies:
        command += " --cookies-from-browser firefox"
    command += f' -f "{BEST_FORMAT}"' if best_format else " -f-"
    command += f' --verbose "{url}"'

    trim = bool(start_time)
    if trim:
        command += f' --download-sections "*{start_time}-{end_time}"'

    if not sub_langs:
        execute_command(f'{command} -o "%(title)s.%(ext)s"')
        return

    # SPERIMENTALE
    # --ignore-errors: un sottotitolo che fallisce (es. HTTP 429) non blocca il download del video
    # --write-subs + --write-auto-subs: sottotitoli manuali preferiti, auto-generati come fallback
    # --sub-format srt/best: SRT nativo (convertire i VTT automatici di YouTube duplica le righe)
    command += f' --ignore-errors --write-subs --write-auto-subs --sub-langs "{sub_langs}" --sub-format "srt/best" --convert-subs srt'

    if not trim:
        # con --write-subs yt-dlp tiene i file dei sottotitoli dopo l'embed:
        # li scrive in una cartella temporanea, cancellata alla fine
        # webm supporta solo sottotitoli WebVTT: remux in mkv prima dell'embed
        tmp_dir = tempfile.mkdtemp(prefix=".ytdlp_utility_tmp_", dir=os.getcwd())
        try:
            subtitle_template = os.path.join(tmp_dir, "%(title)s.%(ext)s")
            execute_command(f'{command} --embed-subs --remux-video "webm>mkv" -o "%(title)s.%(ext)s" -o "subtitle:{subtitle_template}"')
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    start_sec = parse_time_to_seconds(start_time)
    end_sec = parse_time_to_seconds(end_time)  # None (es. "inf") = fino alla fine
    if start_sec is None:
        print("Invalid start time, cannot align subtitles.")
        return
    download_trimmed_video_with_subtitles(command, start_sec, end_sec)

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
def download_subtitles(url, languages="", use_cookies=False):
    """languages vuoto -> tutti i sottotitoli manuali + auto-generati nella lingua originale
    languages impostato -> solo quelle lingue (manuali preferiti, auto-generati come fallback)
    --ignore-errors: una lingua che fallisce (es. HTTP 429) non blocca le altre
    --sub-format srt/best: SRT nativo dal sito; convertire i VTT "roll-up" dei sottotitoli
    automatici di YouTube duplica ogni riga, quindi --convert-subs resta solo come fallback"""
    base = 'yt-dlp --cookies-from-browser firefox' if use_cookies else 'yt-dlp'
    common = f'--ignore-errors --skip-download --sub-format "srt/best" --convert-subs srt -o "%(title)s.%(ext)s" "{url}"'
    if not languages:
        # "all" con --write-auto-subs scaricherebbe anche ~150 traduzioni automatiche (HTTP 429),
        # quindi manuali e auto-generati originali vengono scaricati separatamente
        execute_command(f'{base} --write-subs --sub-langs "all,-live_chat" {common}')
        execute_command(f'{base} --write-auto-subs --sub-langs ".*-orig" {common}')
    else:
        execute_command(f'{base} --write-subs --write-auto-subs --sub-langs "{languages}" {common}')

##* ytdlp CALlS

def ask_embed_subtitles():
    """Ritorna la stringa delle lingue ("" = nessun sottotitolo), None se scelta non valida"""
    choice = get_user_input("[EXPERIMENTAL] Do you want to embed subtitles in the file? (y/n): ").lower()
    if choice == 'n':
        return ""
    if choice != 'y':
        print("Invalid choice")
        return None
    print("Enter subtitle languages separated by comma (e.g. it,en)")
    languages = get_user_input("or press ENTER for the auto-generated ones in the original language (YouTube): ")
    return "".join(languages.split()) or ".*-orig"

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
    start_time, end_time = "", ""
    choice = get_user_input("Do you want to trim the video? (y/n): ").lower()
    if choice == 'y':
        start_time = get_user_input("Enter the start time (hh:mm:ss OR mm:ss): ").strip()
        end_time = get_user_input("Enter the end time (hh:mm:ss OR mm:ss): ").strip()
        print(f"Your selection: *{start_time}-{end_time}")
    elif choice != 'n':
        print("Invalid choice")
        return 1

    # SUBTITLES
    sub_langs = ask_embed_subtitles()
    if sub_langs is None:
        return 1
    
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    print(f"{RED}USE id+id FOR SELECTION{RESET}")
    print(f"{RED}----------------------------------------------------{RESET}")
    
    download_video(url, False, cookies_flag, start_time, end_time, sub_langs)
    
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
    start_time, end_time = "", ""
    choice = get_user_input("Do you want to trim the video? (y/n): ").lower()
    if choice == 'y':
        start_time = get_user_input("Enter the start time (hh:mm:ss OR mm:ss): ").strip()
        end_time = get_user_input("Enter the end time (hh:mm:ss OR mm:ss): ").strip()
        print(f"Your selection: *{start_time}-{end_time}")
    elif choice != 'n':
        print("Invalid choice")
        return 1

    # SUBTITLES
    sub_langs = ask_embed_subtitles()
    if sub_langs is None:
        return 1
    
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    print(f"{RED}----------------------------------------------------{RESET}")
    
    download_video(url, True, cookies_flag, start_time, end_time, sub_langs)
    
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

    # USE OF COOKIES
    choice = get_user_input("Do you want to use cookies? (y/n): ").lower()
    if choice == 'y':
        cookies_flag = True
    elif choice == 'n':
        cookies_flag = False
    else:
        print("Invalid choice")
        return 1

    print("Enter subtitle languages separated by comma (e.g. it,en)")
    languages = "".join(get_user_input("or press ENTER for all manual subtitles + auto-generated in the original language: ").split())
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    print(f"{RED}----------------------------------------------------{RESET}")
    download_subtitles(url, languages, cookies_flag)
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
    print("  --sub       Download subtitles in SRT (manual + auto-generated)")

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