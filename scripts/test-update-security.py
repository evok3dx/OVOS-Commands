#!/usr/bin/env python3
"""Verify release extraction rejects ambiguous or resource-heavy archives."""

from __future__ import annotations

import importlib.util
import io
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("jarvis_update", ROOT / "scripts/update.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def archive(path: Path, entries: list[tuple[str, bytes | None, str]]) -> None:
    with tarfile.open(path, "w:gz") as bundle:
        for name, data, kind in entries:
            member = tarfile.TarInfo(name)
            if kind == "directory":
                member.type = tarfile.DIRTYPE
                member.mode = 0o755
                bundle.addfile(member)
            elif kind == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "elsewhere"
                bundle.addfile(member)
            else:
                content = data or b""
                member.size = len(content)
                member.mode = 0o644
                bundle.addfile(member, io.BytesIO(content))


def rejected(entries, *, members=None, path_length=None):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "release.tar.gz"
        archive(source, entries)
        old_members = module.MAX_ARCHIVE_MEMBERS
        old_length = module.MAX_ARCHIVE_PATH_LENGTH
        if members is not None:
            module.MAX_ARCHIVE_MEMBERS = members
        if path_length is not None:
            module.MAX_ARCHIVE_PATH_LENGTH = path_length
        try:
            try:
                module.safe_extract(source, root / "out")
            except RuntimeError:
                return
            raise AssertionError("unsafe archive was accepted")
        finally:
            module.MAX_ARCHIVE_MEMBERS = old_members
            module.MAX_ARCHIVE_PATH_LENGTH = old_length


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "release.tar.gz"
    archive(source, [
        ("ovos-commands-test", None, "directory"),
        ("ovos-commands-test/scripts", None, "directory"),
        ("ovos-commands-test/scripts/install.sh", b"#!/bin/sh\n", "file"),
    ])
    assert module.safe_extract(source, root / "out").name == "ovos-commands-test"

rejected([
    ("ovos-commands-test", None, "directory"),
    ("ovos-commands-test/scripts", None, "directory"),
    ("ovos-commands-test/scripts/install.sh", b"one", "file"),
    ("ovos-commands-test/scripts/install.sh", b"two", "file"),
])
rejected([
    ("ovos-commands-test", None, "directory"),
    ("ovos-commands-test/scripts", None, "directory"),
    ("ovos-commands-test/scripts/install.sh", None, "symlink"),
])
rejected([
    ("ovos-commands-test", None, "directory"),
    ("ovos-commands-test/scripts", None, "directory"),
], members=1)
rejected([
    ("ovos-commands-test", None, "directory"),
    ("ovos-commands-test/scripts/install.sh", b"ok", "file"),
], path_length=12)

print("PASS: updater rejects duplicate, linked, oversized-count and overlong entries")
