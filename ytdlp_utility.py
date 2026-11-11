#!/usr/bin/python3
"""
Utility interattiva per yt-dlp: costruisce i comandi e li esegue come sottoprocessi.

Nessuna dipendenza Python: basta la libreria standard (Python 3.10+).
Servono solo gli eseguibili yt-dlp, ffmpeg e ffprobe nel PATH.

Vantaggi rispetto a `import yt_dlp`:
- funziona con qualunque yt-dlp installato (binario standalone, pipx, pacchetto di
  sistema) e lo si aggiorna indipendentemente dallo script (`yt-dlp -U`)
- ogni comando viene stampato e si può rilanciare a mano: i flag sono quelli della
  documentazione di yt-dlp
Svantaggi:
- i dati (titolo della playlist, file scaricati) si ricavano da stdout e dal
  filesystem invece che da strutture Python
- un processo yt-dlp per ogni chiamata, errori disponibili solo come exit code
"""

import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from pathlib import Path

SCRIPT_VERSION = 1.6

# Colori per il terminale
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
SEPARATOR = "-" * 52

BEST_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
OUTPUT_TEMPLATE = "%(title)s.%(ext)s"
NUMBERED_TEMPLATE = "%(playlist_index)s-%(title)s.%(ext)s"
COOKIES_ARGS = ("--cookies-from-browser", "firefox")
MP3_ARGS = ("-x", "--audio-format", "mp3", "--embed-thumbnail")
# srt/best: SRT nativo dal sito; convertire i VTT "roll-up" dei sottotitoli automatici
# di YouTube duplica ogni riga, quindi --convert-subs resta solo come fallback
SUB_FORMAT_ARGS = ("--sub-format", "srt/best", "--convert-subs", "srt")
DEFAULT_EMBED_SUB_LANGS = ".*-orig"  # auto-generati nella lingua originale (YouTube)

TMP_PREFIX = ".ytdlp_utility_tmp_"
DEFAULT_PLAYLIST_NAME = "Playlist"
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*%]')
SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")
MP4_SUFFIXES = frozenset({".mp4", ".m4v", ".mov"})
NON_VIDEO_SUFFIXES = frozenset({".srt", ".vtt", ".part", ".ytdl"})
NO_END_MS = 1 << 62

ISO639_2: dict[str, str] = {
    "ar": "ara", "de": "deu", "en": "eng", "es": "spa", "fr": "fra", "hi": "hin",
    "it": "ita", "ja": "jpn", "ko": "kor", "nl": "nld", "pl": "pol", "pt": "por",
    "ro": "ron", "ru": "rus", "sv": "swe", "tr": "tur", "uk": "ukr", "zh": "zho",
}

# (descrizione, solo audio, numerazione)
PLAYLIST_OPTIONS: tuple[tuple[str, bool, bool], ...] = (
    ("Audio mode (mp3) with enumeration (1-NameVideo1.mp3 2-NameVideo2.mp3...)", True, True),
    ("Audio mode (mp3) without enumeration", True, False),
    ("Video+Audio mode (best mp4+m4a) with enumeration (1-NameVideo1.mp4 2-NameVideo2.mp4...)", False, True),
    ("Video+Audio mode (best mp4+m4a) without enumeration", False, False),
)

HELP_TEXT = f"""\
ytdlp_utility v{SCRIPT_VERSION}
Usage: ytdlp_utility [option]
Options:
  (no options)   Video+Audio with full selection of the output format
  --best         Download the best mp4+m4a available format
  -a             Download only the mp3 format
  -p             Enter playlist mode
  --sub          Download subtitles in SRT (manual + auto-generated)
  -h, --help     Show this help message and exit
  -V, --version  Show the version and exit"""


# ---------------------------------------------------------------- processi e file

def run(cmd: Sequence[str]) -> int:
    """
    Esegue il comando senza shell (nessun problema di quoting o injection) e ne ritorna l'exit code
    """
    print(f"Executing: {shlex.join(cmd)}")
    try:
        code = subprocess.run(cmd).returncode
    except FileNotFoundError:
        print(f"{RED}{cmd[0]} is not installed or not in PATH{RESET}")
        return 127
    if code:
        print(f"Command failed with return code {code}")
    return code


def ytdlp(*args: str, cookies: bool = False) -> list[str]:
    """
    Comando yt-dlp con gli argomenti dati, opzionalmente con i cookie di Firefox
    """
    return ["yt-dlp", *(COOKIES_ARGS if cookies else ()), *args]


def output_path(directory: Path, template: str = OUTPUT_TEMPLATE) -> str:
    """
    Template -o dentro directory: i '%' del percorso vanno raddoppiati per yt-dlp
    """
    return str(Path(str(directory).replace("%", "%%")) / template)


@contextmanager
def temp_dir() -> Generator[Path, None, None]:
    """
    Cartella temporanea nella directory corrente (stesso filesystem: i file si spostano con replace)
    """
    with tempfile.TemporaryDirectory(prefix=TMP_PREFIX, dir=Path.cwd(), ignore_cleanup_errors=True) as tmp:
        yield Path(tmp)


def playlist_directory(url: str) -> Path:
    """
    Crea (se manca) e ritorna una cartella con il nome della playlist
    """
    try:
        result = subprocess.run(ytdlp("--flat-playlist", "--playlist-end", "1", "--print", "%(playlist_title)s", url),
                                capture_output=True, text=True)
        title = next(iter(result.stdout.splitlines()), "")
    except OSError as e:
        print(f"Error getting playlist name: {e}")
        title = ""
    directory = Path(INVALID_FILENAME_CHARS.sub("", title).strip(" .") or DEFAULT_PLAYLIST_NAME)
    directory.mkdir(exist_ok=True)
    return directory


def probe_duration(path: Path) -> float | None:
    """
    Durata di un file multimediale in secondi (ffprobe), None se errore
    """
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True)
        return float(result.stdout.strip())
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- tempi e sottotitoli

def parse_time(text: str) -> float | None:
    """
    "hh:mm:ss", "mm:ss" o "ss" (decimali ammessi) -> secondi, None se non valido
    """
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


def parse_srt_timestamp(text: str) -> int | None:
    """
    "hh:mm:ss,mmm" -> millisecondi, None se non valido
    """
    if not (m := SRT_TIME.search(text)):
        return None
    h, mi, s, ms = map(int, m.groups())
    return ((h * 60 + mi) * 60 + s) * 1000 + ms


def format_srt_timestamp(ms: int) -> str:
    """
    Millisecondi -> "hh:mm:ss,mmm"
    """
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def trim_srt(source: Path, target: Path, start_ms: int, end_ms: int) -> None:
    """
    Tiene solo le righe dentro [start_ms, end_ms] e le sposta in modo che start_ms diventi 0
    (yt-dlp --download-sections taglia il video ma non i sottotitoli)
    """
    text = source.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n[ \t]*\n", text):
        lines = [line for line in block.split("\n") if line.strip()]
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None or timing + 1 >= len(lines):
            continue
        start_text, end_text = lines[timing].split("-->", 1)
        cue_start, cue_end = parse_srt_timestamp(start_text), parse_srt_timestamp(end_text)
        if cue_start is None or cue_end is None or cue_end <= start_ms or cue_start >= end_ms:
            continue
        cues.append(f"{len(cues) + 1}\n"
                    f"{format_srt_timestamp(max(cue_start, start_ms) - start_ms)} --> "
                    f"{format_srt_timestamp(min(cue_end, end_ms) - start_ms)}\n"
                    + "\n".join(lines[timing + 1:]) + "\n")
    target.write_text("\n".join(cues), encoding="utf-8")


def keyframe_preroll(video: Path, start_sec: float, end_sec: float | None) -> float:
    """
    Secondi di video prima della selezione: senza ricodifica il taglio parte dal keyframe
    precedente; mp4 nasconde la parte in più con una edit list, mkv/webm no.
    Inizio reale = inizio - (durata file - durata richiesta)
    """
    if end_sec is None or end_sec <= start_sec:
        return 0.0
    file_sec = probe_duration(video)
    if file_sec is None or file_sec <= end_sec - start_sec:
        return 0.0
    return min(file_sec - (end_sec - start_sec), start_sec)


# ---------------------------------------------------------------- download

def download_trimmed_with_subtitles(cmd: list[str], start_sec: float, end_sec: float | None) -> None:
    """
    Trim + sottotitoli: scarica clip e SRT in una cartella temporanea, taglia/sposta gli SRT
    sulla selezione e unisce tutto con ffmpeg (senza ricodifica)
    """
    with temp_dir() as tmp:
        run([*cmd, "-o", output_path(tmp)])

        files = [f for f in tmp.iterdir() if f.is_file()]
        subtitles = sorted(f for f in files if f.suffix == ".srt")
        videos = [f for f in files if f.suffix not in NON_VIDEO_SUFFIXES]
        if not videos:
            print("Video download failed, nothing to do.")
            return
        video = max(videos, key=lambda f: f.stat().st_size)
        if not subtitles:
            print("No subtitles downloaded, saving the video without subtitles.")
            video.replace(Path.cwd() / video.name)
            return

        is_mp4 = video.suffix in MP4_SUFFIXES
        out_suffix = video.suffix if is_mp4 or video.suffix == ".mkv" else ".mkv"  # webm supporta solo WebVTT
        preroll = keyframe_preroll(video, start_sec, end_sec)
        if preroll > 0.1:
            print(f"Video starts {preroll:g}s before the selection (keyframe), subtitles aligned to it")
        start_ms = int((start_sec - preroll) * 1000)
        end_ms = int(end_sec * 1000) if end_sec is not None else NO_END_MS

        inputs, maps, metadata = ["-i", str(video)], ["-map", "0"], []
        for i, sub in enumerate(subtitles, start=1):
            cut = tmp / f"sub{i}.srt"
            trim_srt(sub, cut, start_ms, end_ms)
            lang = Path(sub.stem).suffix.removeprefix(".")  # "Title.it.srt" -> "it"
            inputs += ["-i", str(cut)]
            maps += ["-map", str(i)]
            metadata += [f"-metadata:s:s:{i - 1}", f"language={ISO639_2.get(lang.split('-')[0], lang)}",
                         f"-metadata:s:s:{i - 1}", f"title={lang}"]
        output = tmp / f"output{out_suffix}"
        codec = "mov_text" if is_mp4 else "srt"
        merge = ["ffmpeg", "-v", "error", "-y", *inputs, *maps, "-c", "copy", "-c:s", codec, *metadata, str(output)]
        if run(merge) == 0 and output.exists():
            target = Path.cwd() / f"{video.stem}{out_suffix}"
            output.replace(target)
            print(f"Saved with {len(subtitles)} subtitle track(s): {target.name}")
        else:
            print("ffmpeg failed, saving the video without subtitles.")
            video.replace(Path.cwd() / video.name)


def download_video(url: str, best: bool, cookies: bool, section: tuple[str, str] | None, sub_langs: str) -> None:
    """
    Video+audio: best mp4+m4a oppure selezione interattiva (-f -).
    section = (inizio, fine) per scaricare solo quella parte, None per il video intero.
    sub_langs vuoto = nessun sottotitolo, altrimenti quelle lingue vengono aggiunte come tracce
    """
    args = ["-f", BEST_FORMAT if best else "-", "--verbose", url]
    if section:
        args += ["--download-sections", f"*{section[0]}-{section[1]}"]
    if not sub_langs:
        run(ytdlp(*args, "-o", OUTPUT_TEMPLATE, cookies=cookies))
        return

    # --ignore-errors: un sottotitolo che fallisce (es. HTTP 429) non blocca il video
    # --write-subs + --write-auto-subs: manuali preferiti, auto-generati come fallback
    args += ["--ignore-errors", "--write-subs", "--write-auto-subs", "--sub-langs", sub_langs, *SUB_FORMAT_ARGS]
    if section is None:
        # con --write-subs yt-dlp tiene i file dei sottotitoli dopo l'embed: vanno in una
        # cartella temporanea. webm supporta solo WebVTT: remux in mkv prima dell'embed
        with temp_dir() as tmp:
            run(ytdlp(*args, "--embed-subs", "--remux-video", "webm>mkv", "-o", OUTPUT_TEMPLATE,
                      "-o", f"subtitle:{output_path(tmp)}", cookies=cookies))
        return

    start_sec, end_sec = parse_time(section[0]), parse_time(section[1])  # end None (es. "inf") = fino alla fine
    if start_sec is None:
        print("Invalid start time, cannot align subtitles.")
        return
    download_trimmed_with_subtitles(ytdlp(*args, cookies=cookies), start_sec, end_sec)


def download_audio(url: str) -> None:
    """
    Solo audio mp3 con copertina
    """
    run(ytdlp(*MP3_ARGS, "-o", OUTPUT_TEMPLATE, "--verbose", url))


def download_playlist(url: str, audio: bool, numbered: bool) -> None:
    """
    Playlist in una cartella col suo nome: mp3 con copertina o best mp4+m4a, con numerazione opzionale
    """
    template = output_path(playlist_directory(url), NUMBERED_TEMPLATE if numbered else OUTPUT_TEMPLATE)
    fmt = ["-f", "ba", *MP3_ARGS] if audio else ["-f", BEST_FORMAT]
    run(ytdlp(*fmt, "-o", template, "--yes-playlist", url))


def download_subtitles(url: str, languages: str, cookies: bool) -> None:
    """
    languages vuoto -> tutti i manuali + gli auto-generati nella lingua originale;
    altrimenti solo quelle lingue (manuali preferiti, auto-generati come fallback).
    "all" con --write-auto-subs scaricherebbe ~150 traduzioni automatiche (HTTP 429),
    quindi manuali e auto-generati originali vengono scaricati separatamente
    """
    common = ["--ignore-errors", "--skip-download", *SUB_FORMAT_ARGS, "-o", OUTPUT_TEMPLATE, url]
    if languages:
        passes = [["--write-subs", "--write-auto-subs", "--sub-langs", languages]]
    else:
        passes = [["--write-subs", "--sub-langs", "all,-live_chat"], ["--write-auto-subs", "--sub-langs", ".*-orig"]]
    for selection in passes:
        run(ytdlp(*selection, *common, cookies=cookies))


# ---------------------------------------------------------------- interfaccia

def ask_yes_no(prompt: str) -> bool | None:
    """
    Domanda y/n: True/False, None (con messaggio) se la risposta non è valida
    """
    choice = input(f"{prompt} (y/n): ").strip().lower()
    if choice not in ("y", "n"):
        print("Invalid choice")
        return None
    return choice == "y"


def ask_languages(prompt: str) -> str:
    """
    Lingue separate da virgola, senza spazi ("" se l'utente preme INVIO)
    """
    print("Enter subtitle languages separated by comma (e.g. it,en)")
    return "".join(input(prompt).split())


def start_banner(note: str = "") -> None:
    """
    Intestazione stampata prima di lanciare yt-dlp
    """
    print(f"{RED}\nSTART YT-DLP DOWNLOAD...{RESET}")
    if note:
        print(f"{RED}{note}{RESET}")
    print(f"{RED}{SEPARATOR}{RESET}")


def handle_video(best: bool) -> int:
    """
    Video+audio: best mp4+m4a o selezione manuale del formato, con trim e sottotitoli opzionali
    """
    print("Best MP4+M4A mode selected" if best else "Video+Audio with Selection mode selected")
    url = input("Enter the URL: ")
    if (cookies := ask_yes_no("Do you want to use cookies?")) is None:
        return 1
    if (trim := ask_yes_no("Do you want to trim the video?")) is None:
        return 1
    section = None
    if trim:
        section = (input("Enter the start time (hh:mm:ss OR mm:ss): ").strip(),
                   input("Enter the end time (hh:mm:ss OR mm:ss): ").strip())
        print(f"Your selection: *{section[0]}-{section[1]}")
    if (embed := ask_yes_no("[EXPERIMENTAL] Do you want to embed subtitles in the file?")) is None:
        return 1
    sub_langs = ""
    if embed:
        sub_langs = ask_languages("or press ENTER for the auto-generated ones in the original language (YouTube): ") \
            or DEFAULT_EMBED_SUB_LANGS
    start_banner("" if best else "USE id+id FOR SELECTION")
    download_video(url, best, cookies, section, sub_langs)
    return 0


def handle_audio() -> int:
    """
    Solo audio mp3
    """
    print("Audio mode selected, download the mp3 format")
    url = input("Enter the URL: ")
    start_banner()
    download_audio(url)
    return 0


def handle_playlist() -> int:
    """
    Playlist: scelta tra le combinazioni di PLAYLIST_OPTIONS
    """
    print("Playlist mode selected")
    url = input("Enter the URL: ")
    print("Enter format:")
    for number, (description, _, _) in enumerate(PLAYLIST_OPTIONS, start=1):
        print(f"{number}) {description}")
    choice = input("Select number: ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(PLAYLIST_OPTIONS):
        print("Invalid choice")
        return 1
    _, audio, numbered = PLAYLIST_OPTIONS[int(choice) - 1]
    start_banner()
    download_playlist(url, audio, numbered)
    return 0


def handle_subtitles() -> int:
    """
    Solo sottotitoli in SRT
    """
    print("Subtitles mode selected")
    url = input("Enter the URL: ")
    if (cookies := ask_yes_no("Do you want to use cookies?")) is None:
        return 1
    languages = ask_languages("or press ENTER for all manual subtitles + auto-generated in the original language: ")
    start_banner()
    download_subtitles(url, languages, cookies)
    return 0


def main(argv: list[str]) -> int:
    """
    Sceglie la modalità dall'argomento (nessuno = video con selezione del formato)
    """
    modes: dict[str, Callable[[], int]] = {
        "": lambda: handle_video(best=False),
        "--best": lambda: handle_video(best=True),
        "-a": handle_audio,
        "-p": handle_playlist,
        "--sub": handle_subtitles,
    }
    if len(argv) > 1:
        print("Too many arguments")
        return 1
    arg = argv[0] if argv else ""
    if arg in ("-h", "--help"):
        print(HELP_TEXT)
        return 0
    if arg in ("-V", "--version"):
        print(SCRIPT_VERSION)
        return 0
    if arg not in modes:
        print("Invalid argument")
        return 1
    try:
        result = modes[arg]()
        print(f"{GREEN}{SEPARATOR}\nEND YT-DLP UTILITY EXECUTION...{RESET}")
        input("Premi INVIO per continuare...")
    except (KeyboardInterrupt, EOFError):
        print(f"\n{RED}Operazione annullata dall'utente{RESET}")
        return 130
    return result


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
