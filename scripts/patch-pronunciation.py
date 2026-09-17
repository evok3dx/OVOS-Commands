#!/usr/bin/env python3
"""Apply the reviewed Misaki eSpeak fallback used by the working Brain."""

from __future__ import annotations

import argparse
import importlib.util
import py_compile
import re
import shutil
from pathlib import Path


OLD = """                if self.g2p_en is None:
                    from misaki import en
                    self.g2p_en = en.G2P()
"""
NEW = """                if self.g2p_en is None:
                    from misaki import en
                    from misaki.espeak import EspeakFallback
                    british = lang == \"en-GB\"
                    self.g2p_en = en.G2P(
                        british=british,
                        fallback=EspeakFallback(british=british),
                    )
"""


def layout(source: str) -> str:
    """Classify the installed fallback without depending on formatting."""
    fallback = re.search(
        r"fallback\s*=\s*EspeakFallback\(\s*british\s*=\s*british\s*\)\s*,?",
        source,
    )
    if (
        "from misaki.espeak import EspeakFallback" in source
        and 'british = lang == "en-GB"' in source
        and fallback
    ):
        return "already-applied"
    if OLD in source:
        return "needs-patch"
    raise RuntimeError(
        "The installed scriptconv source is not the reviewed layout; "
        "refusing an unsafe pronunciation patch."
    )


def source_path() -> Path:
    spec = importlib.util.find_spec("scriptconv.phonemizers.mul")
    if spec is None or not spec.origin:
        raise RuntimeError("scriptconv.phonemizers.mul is not installed")
    return Path(spec.origin)


def patch(path: Path, backup: Path | None = None) -> str:
    source = path.read_text(encoding="utf-8")
    state = layout(source)
    if state == "already-applied":
        return "already-applied"
    if backup is not None:
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    temporary = path.with_suffix(path.suffix + ".jarvis-new")
    temporary.write_text(source.replace(OLD, NEW, 1), encoding="utf-8")
    temporary.chmod(path.stat().st_mode & 0o777)
    py_compile.compile(str(temporary), doraise=True)
    temporary.replace(path)
    return "applied"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--print-source", action="store_true")
    args = parser.parse_args()
    path = source_path()
    if args.print_source:
        print(path)
        return 0
    result = patch(path, args.backup)
    print(f"Pronunciation fallback {result}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
