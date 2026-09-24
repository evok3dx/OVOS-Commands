"""Show filename matches and open only a file explicitly selected by the user."""

from html import escape
from pathlib import Path
from shutil import which
import fcntl
import os
import signal
import subprocess
import sys


def show_results(query, matches, truncated=False):
    """Replace the prior result window and start a separate UI process."""
    if not (which("zenity") and which("xdg-open")):
        return False
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    args = [sys.executable, "-m", "jarvis_file_search.results",
            "1" if truncated else "0", query]
    args.extend(str(match.path) for match in matches)
    state_dir = Path.home() / ".cache" / "jarvis-file-search"
    try:
        state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_fd = os.open(state_dir / "window.lock", os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(lock_fd, "r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            previous = lock.read().strip()
            if previous.isdecimal():
                pid = int(previous)
                if _is_our_window(pid):
                    try:
                        os.killpg(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL,
                                       start_new_session=True)
            lock.seek(0)
            lock.write(str(process.pid))
            lock.truncate()
    except OSError:
        return False
    return True


def _is_our_window(pid):
    """Avoid signalling stale or unrelated process IDs from an old lock file."""
    try:
        command = (Path("/proc") / str(pid) / "cmdline").read_bytes().split(b"\0")
        return (len(command) >= 4 and command[1:3] ==
                [b"-m", b"jarvis_file_search.results"] and os.getpgid(pid) == pid)
    except (OSError, ValueError):
        return False


def run_window(query, paths, truncated=False):
    """Block in the UI subprocess until the user selects Open or closes it."""
    zenity = which("zenity")
    opener = which("xdg-open")
    if not zenity or not opener:
        return False
    explanation = (f"Filename matches for: {query}. Double-click a file or select it and click Open."
                   if paths else f"No matching filenames for: {query}.")
    if truncated:
        explanation += " Results may be incomplete."
    args = [zenity, "--list", "--title=Jarvis file search",
            "--text=" + escape(explanation), "--width=900", "--height=480",
            "--column=File", "--column=Folder", "--ok-label=Open",
            "--cancel-label=Close", "--"]
    selected = {}
    for index, path in enumerate(paths, start=1):
        label = f"{index}. {path.name}".replace("\n", " ").replace("\t", " ")
        selected[label] = path
        args.extend((label, str(path.parent).replace("\n", " ").replace("\t", " ")))
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, check=False)
    if result.returncode != 0:
        return False
    path = selected.get(result.stdout.strip())
    if path is None or path.is_symlink() or not path.is_file():
        return False
    subprocess.Popen([opener, str(path)], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        run_window(sys.argv[2], [Path(p) for p in sys.argv[3:]],
                   truncated=sys.argv[1] == "1")
