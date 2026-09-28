#!/usr/bin/env python3
"""Verify release extraction rejects ambiguous or resource-heavy archives."""

from __future__ import annotations

import importlib.util
import io
import os
import stat
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("jarvis_update", ROOT / "scripts/update.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


with tempfile.TemporaryDirectory() as directory:
    previous_home = os.environ.get("JARVIS_HOME")
    os.environ["JARVIS_HOME"] = directory
    try:
        private_work = module.work_dir()
        assert private_work == Path(directory) / ".local/state/jarvis/updates/work"
        assert stat.S_IMODE(private_work.stat().st_mode) == 0o700
    finally:
        if previous_home is None:
            os.environ.pop("JARVIS_HOME", None)
        else:
            os.environ["JARVIS_HOME"] = previous_home


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
rejected([
    ("ovos-commands-test", None, "directory"),
    ("ovos-commands-test/scripts", None, "directory"),
    ("ovos-commands-test/scripts/./install.sh", b"ok", "file"),
])

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    previous_home = os.environ.get("JARVIS_HOME")
    os.environ["JARVIS_HOME"] = directory
    target = root / ".local/state/jarvis/updates/work"
    target.parent.mkdir(parents=True)
    target.symlink_to(root / "elsewhere", target_is_directory=True)
    try:
        try:
            module.work_dir()
        except RuntimeError:
            pass
        else:
            raise AssertionError("symbolic-link update workspace was accepted")
    finally:
        if previous_home is None:
            os.environ.pop("JARVIS_HOME", None)
        else:
            os.environ["JARVIS_HOME"] = previous_home

print("PASS: updater uses private user staging and rejects unsafe archives")
