#!/usr/bin/env python3
"""Retarget console launchers after pip installs into a staged OVOS venv."""

import os
import re
import stat
import sys
import tempfile
from pathlib import Path


def relocate(staged: Path, final: Path) -> list[str]:
    staged = staged.resolve(strict=True)
    final = final.absolute()
    if staged == final or not (staged / "bin/python").exists():
        raise ValueError("Invalid staged OVOS virtualenv")
    if final.is_symlink() or not final.parent.is_dir():
        raise ValueError("Invalid destination for OVOS virtualenv")

    changed = []
    marker = ("#!" + str(staged / "bin") + "/").encode()
    # An interrupted V3.1 install may already have left entry points pointing
    # to a *previous* removed stage. Copying that venv carries them forward.
    older_stage = re.compile(
        rb"^#!" + re.escape(os.fsencode(final.parents[1])) +
        rb"/\.local/state/jarvis/stage\.[A-Za-z0-9._-]+/ovos-venv/bin/"
        rb"(python(?:3(?:\.\d+)?)?)$"
    )
    for path in sorted((staged / "bin").iterdir()):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as stream:
            first = stream.readline(512).rstrip(b"\r\n")
            if (first.startswith(b"#!/var/tmp/jarvis-ovos-root.")
                    or first.startswith(b"#!/tmp/jarvis-ovos-installer.")):
                raise ValueError(f"Launcher refers to privileged installer scratch: {path.name}")
            previous = older_stage.fullmatch(first)
            if first.startswith(marker):
                interpreter = first[len(marker):]
            elif previous:
                interpreter = previous.group(1)
            else:
                if b"/.local/state/jarvis/stage." in first and b"/ovos-venv/bin/" in first:
                    raise ValueError(f"Unrecognised staged launcher path: {path.name}")
                continue
            if not re.fullmatch(rb"python(?:3(?:\.\d+)?)?", interpreter):
                raise ValueError(f"Unrecognised staged launcher interpreter: {path.name}")
        destination = final / "bin" / interpreter.decode("ascii")
        if not (staged / "bin" / interpreter.decode("ascii")).exists():
            raise ValueError(f"Missing OVOS interpreter for {path.name}")
        current = path.read_bytes()
        if b"\n" not in current:
            raise ValueError(f"Incomplete OVOS launcher: {path.name}")
        updated = b"#!" + os.fsencode(destination) + b"\n" + current.split(b"\n", 1)[1]
        mode = stat.S_IMODE(path.stat().st_mode)
        fd, temporary = tempfile.mkstemp(prefix=".jarvis-launcher-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(updated)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temporary, mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        changed.append(path.name)

    for name in ("ovos-core", "ovos-audio", "ovos-dinkum-listener"):
        path = staged / "bin" / name
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"Required OVOS service launcher missing: {name}")
        first = path.open("rb").readline(512).rstrip(b"\r\n")
        if first.startswith(b"#!"):
            executable = first[2:].decode("utf-8", "replace").split(" ", 1)[0]
            if executable.startswith(str(staged / "bin")) or (
                executable.startswith(str(final / "bin")) and
                not (staged / "bin" / Path(executable).name).exists()
            ):
                raise ValueError(f"Broken OVOS launcher interpreter: {name}")
    return changed


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: relocate-ovos-launchers.py STAGED_VENV FINAL_VENV")
    try:
        names = relocate(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print("Prepared OVOS launchers for the final virtualenv: " +
          (", ".join(names) if names else "no retargeting needed"))
