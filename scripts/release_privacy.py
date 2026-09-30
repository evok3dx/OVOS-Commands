#!/usr/bin/env python3
"""Reject private captures before packaging; never print their contents."""
import os
from pathlib import PurePosixPath
import sys

BLOCKED = {'.env', 'mycroft.conf', 'settings.json', 'credentials.json',
           'id_rsa', 'id_ed25519'}
EXTENSIONS = {'.key', '.token', '.log', '.onnx', '.gguf', '.ses',
              '.sqlite', '.sqlite3'}


def check_path(relative):
    path = PurePosixPath(relative)
    if (path.is_absolute() or '..' in path.parts
            or any(part in BLOCKED or part.startswith('runtime-observed-')
                   for part in path.parts)
            or path.suffix in EXTENSIONS):
        raise ValueError('Private or unreviewed artifact cannot enter a release')


if __name__ == '__main__':
    try:
        for raw in sys.stdin.buffer.read().split(b'\0'):
            if raw:
                check_path(os.fsdecode(raw))
    except ValueError:
        sys.exit('BLOCKED: private or unreviewed artifact in release file list')
