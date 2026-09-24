#!/usr/bin/env python3
"""Refuse an upgrade whose existing private plugin cannot be reinstalled."""
import importlib.metadata as metadata
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit


PLUGINS = ("jarvis-file-search-skill", "ovos-skill-jarvis-media")


def missing_source(direct_url):
    if not direct_url:
        return False
    parsed = urlsplit(direct_url.get("url", ""))
    if parsed.scheme != "file":
        return False
    return parsed.netloc not in ("", "localhost") or not Path(unquote(parsed.path)).exists()


def main():
    missing = []
    for package in PLUGINS:
        try:
            source = metadata.distribution(package).read_text("direct_url.json")
        except metadata.PackageNotFoundError:
            continue
        if source and missing_source(json.loads(source)):
            missing.append(package)
    if missing:
        raise SystemExit(
            "Cannot safely upgrade: the previous local installer source for "
            + ", ".join(missing)
            + " is missing. Keep or restore its original package before V3 so rollback can reinstall it."
        )
    print("Existing local plugin rollback sources are available.")


if __name__ == "__main__":
    main()
