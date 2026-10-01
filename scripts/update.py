#!/usr/bin/env python3
"""Check and install verified Jarvis releases from a configured GitHub repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
VERSION = str(POLICY["release_version"])
MAX_ARCHIVE_MEMBERS = 4096
MAX_ARCHIVE_PATH_LENGTH = 240
UPDATE_HOSTS = frozenset({'api.github.com', 'github.com',
                          'release-assets.githubusercontent.com',
                          'objects.githubusercontent.com'})


def validate_update_url(url: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in UPDATE_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.fragment):
        raise RuntimeError('Update transport rejected an untrusted URL')


class UpdateRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        validate_update_url(new_url)
        return super().redirect_request(request, response, code, message, headers, new_url)


def open_update(request, timeout):
    validate_update_url(request.full_url)
    return urllib.request.build_opener(UpdateRedirectHandler()).open(request, timeout=timeout)


def home() -> Path:
    return Path(os.environ.get("JARVIS_HOME", Path.home())).expanduser()


def state_dir() -> Path:
    return home() / ".local/state/jarvis/updates"


def work_dir() -> Path:
    """Private user-owned space for downloaded and extracted releases."""
    directory = state_dir() / "work"
    if directory.is_symlink():
        raise RuntimeError("Update workspace must not be a symbolic link")
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise RuntimeError("Update workspace is not a directory")
    directory.chmod(0o700)
    return directory


def repository() -> str:
    configured = POLICY.get("updates", {}).get("repository")
    user_config = home() / ".config/jarvis/update.json"
    if user_config.is_file():
        data = json.loads(user_config.read_text(encoding="utf-8"))
        configured = data.get("repository", configured)
    value = str(configured or "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise RuntimeError(
            "Updates are not configured yet. Set the GitHub repository in "
            "~/.config/jarvis/update.json after publishing the first release."
        )
    return value


def request_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": "Jarvis-Updater"},
    )
    with open_update(request, timeout=20) as response:
        return json.load(response)


def download(url: str, destination: Path, limit: int = 100_000_000, *, progress=None) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Jarvis-Updater"})
    with open_update(request, timeout=60) as response, destination.open("wb") as stream:
        written = 0
        while chunk := response.read(1024 * 1024):
            written += len(chunk)
            if written > limit:
                raise RuntimeError("Release download exceeds the 100 MB safety limit")
            stream.write(chunk)
            if progress is not None:
                progress(written, limit)


def version_key(value: str) -> tuple[int, ...]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?", value.strip())
    if not match:
        raise RuntimeError(f"Unsupported release version: {value}")
    major, minor, patch, candidate = match.groups()
    return (int(major), int(minor), int(patch), 0 if candidate else 1,
            int(candidate) if candidate else 0)


def latest_release() -> dict[str, object]:
    data = request_json(f"https://api.github.com/repos/{repository()}/releases/latest")
    version = str(data.get("tag_name", "")).removeprefix("v")
    version_key(version)
    assets = {
        str(asset.get("name")): str(asset.get("browser_download_url"))
        for asset in data.get("assets", []) if isinstance(asset, dict)
    }
    archive = f"ovos-commands-{version}.tar.gz"
    checksum = f"{archive}.sha256"
    if archive not in assets or checksum not in assets:
        raise RuntimeError("Latest release is missing its archive or SHA-256 checksum")
    return {
        "version": version,
        "archive": assets[archive],
        "checksum": assets[checksum],
        "release_date": str(data.get("published_at", ""))[:10],
    }


def save_status(release: dict[str, object]) -> bool:
    available = version_key(str(release["version"])) > version_key(VERSION)
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "latest.json"
    temporary = path.with_suffix(".json.new")
    temporary.write_text(json.dumps({
        "schema_version": 1,
        "installed": VERSION,
        "latest": release["version"],
        "release_date": release.get("release_date", ""),
        "update_available": available,
        "check_succeeded": True,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)
    return available


def check(quiet: bool = False) -> tuple[dict[str, object], bool]:
    try:
        release = latest_release()
    except (OSError, RuntimeError, ValueError, urllib.error.URLError):
        directory = state_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / 'latest.json'
        fd, name = tempfile.mkstemp(prefix='.check-', dir=directory)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'schema_version': 1, 'installed': VERSION,
                       'check_succeeded': False, 'update_available': False}, stream)
        Path(name).replace(path)
        raise
    available = save_status(release)
    if not quiet:
        if available:
            print(f"Jarvis {release['version']} is available. Installed: {VERSION}.")
            print("Run 'jarvis-update install' to review and install it.")
        else:
            print(f"Jarvis is up to date ({VERSION}).")
    return release, available


def expected_checksum(path: Path, archive_name: str) -> str:
    line = path.read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?(.+)", line)
    if not match or Path(match.group(2)).name != archive_name:
        raise RuntimeError("Release checksum file is malformed")
    return match.group(1).lower()


def safe_extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise RuntimeError("Release contains too many archive entries")
        total_size = 0
        names: set[str] = set()
        for member in members:
            path = PurePosixPath(member.name)
            normalised = str(path)
            archive_spelling = member.name.rstrip("/")
            total_size += member.size
            if total_size > 100_000_000 or member.size > 20_000_000:
                raise RuntimeError("Release contents exceed the extraction safety limit")
            if (
                path.is_absolute() or ".." in path.parts
                or not normalised or normalised == "."
                or archive_spelling != normalised
                or len(member.name) > MAX_ARCHIVE_PATH_LENGTH
                or normalised in names
                or not (member.isdir() or member.isreg())
            ):
                raise RuntimeError(f"Unsafe release entry: {member.name}")
            names.add(normalised)
        if hasattr(tarfile, 'data_filter'):
            bundle.extractall(destination, filter='data')
        else:
            bundle.extractall(destination)
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1 or not (roots[0] / "scripts/install.sh").is_file():
        raise RuntimeError("Release archive has an unexpected layout")
    return roots[0]


def install(assume_yes: bool) -> int:
    release, available = check(quiet=True)
    if not available:
        print(f"Jarvis is already up to date ({VERSION}).")
        return 0
    if not assume_yes:
        answer = input(
            f"Install Jarvis {release['version']} with automatic rollback protection? [y/N] "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            print("Update cancelled.")
            return 0
    with tempfile.TemporaryDirectory(
        prefix="jarvis-update-", dir=work_dir()
    ) as temporary_name:
        temporary = Path(temporary_name)
        archive_name = f"ovos-commands-{release['version']}.tar.gz"
        archive = temporary / archive_name
        checksum = temporary / f"{archive_name}.sha256"
        download(str(release["archive"]), archive)
        download(str(release["checksum"]), checksum)
        expected = expected_checksum(checksum, archive_name)
        digest = hashlib.sha256()
        with archive.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual != expected:
            raise RuntimeError("Release SHA-256 verification failed")
        release_root = safe_extract(archive, temporary / "extracted")
        command = ["bash", str(release_root / "scripts/install.sh")]
        if os.environ.get("JARVIS_HOME"):
            environment = {**os.environ, "JARVIS_HOME": os.environ["JARVIS_HOME"]}
        else:
            environment = os.environ.copy()
        return subprocess.run(command, env=environment, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--quiet", action="store_true")
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("--yes", action="store_true")
    subparsers.add_parser("rollback")
    args = parser.parse_args()
    if args.command == "check":
        try:
            check(args.quiet)
        except (
            OSError,
            RuntimeError,
            ValueError,
            json.JSONDecodeError,
            urllib.error.URLError,
        ):
            # The scheduled check must remain invisible when the repository is
            # private, the laptop is offline or GitHub is temporarily
            # unavailable. An explicit check still reports the real error via
            # the outer handler below.
            if args.quiet:
                return 0
            raise
        return 0
    if args.command == "install":
        return install(args.yes)
    rollback = ROOT / "scripts/rollback.sh"
    return subprocess.run(["bash", str(rollback)], check=False).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"Jarvis update failed: {error}", file=sys.stderr)
        raise SystemExit(1)
