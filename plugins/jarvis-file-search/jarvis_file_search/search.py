"""Read directory entries and filesystem metadata only; never read file contents."""

from dataclasses import dataclass
from pathlib import Path
import os
import re
import time


@dataclass(frozen=True)
class Match:
    path: Path
    score: int
    modified: float


def _words(value):
    return re.findall(r"[^\W_]+", value.casefold(), flags=re.UNICODE)


def _score(filename, query):
    stem = Path(filename).stem.casefold()
    words = _words(query)
    if not words:
        return 0
    name_words = _words(stem)
    if stem == " ".join(words):
        return 100
    if all(word in name_words for word in words):
        return 80
    if all(word in stem for word in words):
        return 50
    return 0


def search_filenames(query, roots, *, limit=5, max_entries=50000, timeout=3.0):
    """Search regular files by basename within roots, without following symlinks.

    The entry and wall-clock limits prevent a large mount from blocking OVOS.
    Returns (matches, truncated). Results are sorted by relevance then recency.
    """
    if not isinstance(query, str) or not query.strip():
        return [], False
    limit = max(1, min(int(limit), 20))
    max_entries = max(1, int(max_entries))
    deadline = time.monotonic() + max(0.01, float(timeout))
    found = []
    seen = set()
    scanned = 0
    truncated = False

    for root in roots:
        folder = Path(root).expanduser()
        if folder.is_symlink() or not folder.is_dir():
            continue
        # os.walk does not follow directory symlinks with this setting.
        for base, dirs, files in os.walk(folder, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                             and d != "__pycache__"
                             and not (Path(base) / d).is_symlink())
            for name in sorted(files):
                scanned += 1
                if scanned > max_entries or time.monotonic() >= deadline:
                    truncated = True
                    break
                if (name.startswith(".") or name.endswith("~")
                        or name.endswith((".pyc", ".pyo"))):
                    continue
                score = _score(name, query)
                if not score:
                    continue
                path = Path(base) / name
                try:
                    if path.is_symlink() or not path.is_file():
                        continue
                    stat = path.stat()
                except OSError:
                    continue
                if path in seen:
                    continue
                seen.add(path)
                found.append(Match(path, score, stat.st_mtime))
            if truncated:
                break
            if time.monotonic() >= deadline:
                truncated = True
                break
        if truncated:
            break
    found.sort(key=lambda item: (-item.score, -item.modified, str(item.path)))
    return found[:limit], truncated
