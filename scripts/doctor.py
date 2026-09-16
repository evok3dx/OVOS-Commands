#!/usr/bin/env python3
"""Read-only compatibility and deployment diagnostics for Jarvis on OVOS."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))


@dataclass
class Finding:
    level: str
    check: str
    message: str


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self.details: dict[str, object] = {}

    def add(self, level: str, check: str, message: str) -> None:
        self.findings.append(Finding(level, check, message))

    def pass_(self, check: str, message: str) -> None:
        self.add("PASS", check, message)

    def warn(self, check: str, message: str) -> None:
        self.add("WARN", check, message)

    def fail(self, check: str, message: str) -> None:
        self.add("FAIL", check, message)

    @property
    def exit_code(self) -> int:
        return 1 if any(item.level == "FAIL" for item in self.findings) else 0

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "status": "fail" if self.exit_code else "pass",
            "release_version": POLICY["release_version"],
            "findings": [asdict(item) for item in self.findings],
            "details": self.details,
        }


def parse_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def locate_ovos_python(home: Path, explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("OVOS_PYTHON"):
        candidates.append(Path(os.environ["OVOS_PYTHON"]).expanduser())
    for candidate in POLICY["ovos"]["python_candidates"]:
        candidates.append(Path(candidate.replace("~", str(home), 1)))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            # Keep the virtualenv launcher path. Resolving its symlink to the
            # uv-managed base interpreter discards the venv's site-packages.
            return candidate
    return None


def run_json(command: list[str], timeout: int = 20) -> dict[str, object]:
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return json.loads(result.stdout)


def check_ovos_python(report: Report, python: Path | None) -> None:
    if python is None:
        report.fail(
            "ovos-python",
            "OVOS virtualenv was not found; expected ~/.venvs/ovos/bin/python "
            "or OVOS_PYTHON.",
        )
        return

    probe = r'''
import importlib.metadata as metadata
import json

from ovos_workshop.decorators import intent_handler
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.skills.converse import ConversationalSkill

names = [
    "ovos-core", "ovos-workshop", "ovos-config", "ovos-plugin-manager",
    "ovos-audio", "ovos-dinkum-listener", "ovos-skill-jarvis-dispatcher"
]
versions = {}
for name in names:
    try:
        versions[name] = metadata.version(name)
    except metadata.PackageNotFoundError:
        versions[name] = None

groups = sorted({entry.group for entry in metadata.entry_points()})
opm_skill_names = sorted(
    entry.name for entry in metadata.entry_points()
    if entry.group == "opm.skill"
)
print(json.dumps({
    "python": __import__("sys").version.split()[0],
    "versions": versions,
    "has_opm_skill": "opm.skill" in groups,
    "opm_skill_names": opm_skill_names,
    "api": {
        "intent_handler": callable(intent_handler),
        "IntentBuilder": callable(IntentBuilder),
        "ConversationalSkill": callable(ConversationalSkill),
    },
}))
'''
    try:
        data = run_json([str(python), "-c", probe])
    except (subprocess.SubprocessError, json.JSONDecodeError) as error:
        report.fail("ovos-api", f"OVOS API probe failed: {error}")
        return

    report.details["ovos"] = data
    report.pass_("ovos-python", f"Using {python} (Python {data['python']}).")
    if all(data["api"].values()):
        report.pass_("ovos-api", "Required OVOS Workshop APIs are available.")
    else:
        report.fail("ovos-api", "One or more required OVOS Workshop APIs are missing.")

    installed = data["versions"].get("ovos-skill-jarvis-dispatcher")
    expected_entry = POLICY["ovos"]["entry_point_name"]
    if installed == POLICY["release_version"]:
        report.pass_("jarvis-package", f"Jarvis package {installed} is installed.")
    elif installed:
        report.warn(
            "jarvis-package",
            f"Installed Jarvis package is {installed}; release is "
            f"{POLICY['release_version']}.",
        )
    else:
        report.warn("jarvis-package", "Jarvis package is not installed in the OVOS venv.")

    if installed and expected_entry not in data["opm_skill_names"]:
        report.fail(
            "jarvis-entry-point",
            f"Installed package does not expose {expected_entry!r} in opm.skill.",
        )
    elif installed:
        report.pass_(
            "jarvis-entry-point",
            f"OVOS entry point {expected_entry!r} is registered.",
        )


def command_exists(names: Iterable[str]) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def flatpak_installed(application_id: str) -> bool:
    flatpak = shutil.which("flatpak")
    if flatpak is None:
        return False
    try:
        result = subprocess.run(
            [flatpak, "info", application_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def check_commands(report: Report, profile: dict[str, object]) -> None:
    requirements = {
        "desktop-control": ("xdotool",),
        "window-metadata": ("xprop",),
        "window-management": ("wmctrl",),
        "clipboard": ("xclip",),
        "audio-control": ("wpctl", "pactl"),
        "service-control": ("systemctl",),
    }
    found: dict[str, str | None] = {}
    for label, names in requirements.items():
        match = command_exists(names)
        found[label] = match
        if match:
            report.pass_(label, f"Found {match}.")
        else:
            report.fail(label, f"Missing required command: {' or '.join(names)}.")

    optional_by_integration = {
        "brave": (("brave-browser-stable", "brave"), "com.brave.Browser", ()),
        "firefox": (("firefox",), None, ()),
        "signal": (("signal-desktop",), "org.signal.Signal", ("/opt/Signal/signal-desktop",)),
        "zoom": (("zoom",), None, ()),
        "terminal": (("gnome-terminal", "x-terminal-emulator"), None, ()),
        "onlyoffice": (
            ("desktopeditors", "onlyoffice-desktopeditors"),
            "org.onlyoffice.desktopeditors",
            ("/opt/onlyoffice/desktopeditors/DesktopEditors",),
        ),
        "claude_desktop": (("claude-desktop",), None, ("/usr/bin/claude-desktop",)),
        "chatgpt_desktop": (("chatgpt",), None, ("/usr/bin/chatgpt",)),
        "proton_mail": (("proton-mail",), None, ()),
    }
    applications = profile.get("applications", {})
    for integration in sorted(set(applications.values())):
        launchers = optional_by_integration.get(integration)
        if not launchers:
            continue
        names, flatpak_id, absolute_paths = launchers
        match = command_exists(names)
        absolute_match = next((path for path in absolute_paths if Path(path).is_file()), None)
        if match or absolute_match:
            report.pass_(f"app-{integration}", f"Found {match or absolute_match}.")
        elif flatpak_id and flatpak_installed(flatpak_id):
            report.pass_(f"app-{integration}", f"Found Flatpak {flatpak_id}.")
        else:
            report.warn(
                f"app-{integration}",
                f"No launcher found for optional integration {integration}.",
            )
    report.details["commands"] = found


def load_and_validate_profile(path: Path) -> dict[str, object]:
    module_path = ROOT / "ovos_skill_jarvis_dispatcher" / "profile.py"
    spec = importlib.util.spec_from_file_location("jarvis_profile", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load profile validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw = json.loads(path.read_text(encoding="utf-8"))
    module.resolve_profile(raw)
    return raw


def check_services(report: Report, test_mode: bool) -> None:
    if test_mode or shutil.which("systemctl") is None:
        report.warn("ovos-services", "Service probe skipped in test mode.")
        return
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", "ovos.service", "--property=LoadState"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.SubprocessError as error:
        report.warn("ovos-services", f"Could not query user services: {error}")
        return
    if result.returncode == 0 and "LoadState=loaded" in result.stdout:
        report.pass_("ovos-services", "Official ovos.service meta unit is installed.")
    else:
        report.warn(
            "ovos-services",
            "ovos.service was not found in user scope; this may be an older or "
            "system-scope installation.",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=os.environ.get("JARVIS_PROFILE"))
    parser.add_argument("--home", default=os.environ.get("JARVIS_HOME", str(Path.home())))
    parser.add_argument("--ovos-python")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--test-mode", action="store_true")
    args = parser.parse_args()

    report = Report()
    home = Path(args.home).expanduser().resolve()
    if args.profile:
        profile_path = ROOT / "profiles" / f"{args.profile}.json"
        configuration_label = f"legacy profile {args.profile}"
    else:
        installed_capabilities = home / ".config/jarvis/capabilities.json"
        installed_profile = home / ".config/jarvis/profile.json"
        if installed_capabilities.is_file():
            profile_path = installed_capabilities
            configuration_label = "installed capabilities"
        elif installed_profile.is_file():
            profile_path = installed_profile
            configuration_label = "installed legacy profile"
        else:
            profile_path = ROOT / "profiles/portable-desktop.json"
            configuration_label = "portable fallback"
    report.details["configuration"] = configuration_label

    os_release = parse_os_release()
    report.details["host"] = {
        "system": platform.system(),
        "architecture": platform.machine(),
        "os_id": os_release.get("ID"),
        "os_version": os_release.get("VERSION_ID"),
        "session": os.environ.get("XDG_SESSION_TYPE"),
    }
    if platform.system() == "Linux":
        report.pass_("host-os", "Linux host detected.")
    else:
        report.fail("host-os", "This desktop integration release supports Linux only.")

    os_id = os_release.get("ID", "unknown")
    if os_id in POLICY["support"]["validated_distributions"]:
        report.pass_("host-family", f"Validated distribution detected: {os_id}.")
    elif os_id in POLICY["support"]["compatible_families"]:
        report.warn(
            "host-family",
            f"Compatible Linux family detected but not machine-validated: {os_id}.",
        )
    else:
        report.warn("host-family", f"Distribution {os_id} has not been validated.")

    architecture = platform.machine()
    if architecture in POLICY["support"]["architectures"]:
        report.pass_("architecture", f"Validated architecture: {architecture}.")
    else:
        report.warn("architecture", f"Architecture {architecture} is not yet validated.")

    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "x11" or (not session and os.environ.get("DISPLAY")):
        report.pass_("desktop-session", "X11 desktop session detected.")
    elif session == "wayland":
        report.fail(
            "desktop-session",
            "Wayland is not supported by the allowlisted xdotool/wmctrl controls; "
            "log into an X11 session.",
        )
    else:
        report.warn("desktop-session", "Desktop session could not be identified.")

    try:
        profile = load_and_validate_profile(profile_path)
        report.pass_("profile", f"Jarvis {configuration_label} validates.")
        check_commands(report, profile)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        report.fail("profile", f"Profile validation failed: {error}")

    ovos_python = locate_ovos_python(home, args.ovos_python)
    check_ovos_python(report, ovos_python)
    check_services(report, args.test_mode or os.environ.get("JARVIS_TEST_MODE") == "1")

    if args.json:
        print(json.dumps(report.to_json(), indent=2, sort_keys=True))
    else:
        for item in report.findings:
            print(f"{item.level:4} {item.check:20} {item.message}")
        failures = sum(item.level == "FAIL" for item in report.findings)
        warnings = sum(item.level == "WARN" for item in report.findings)
        print(f"\nResult: {failures} failure(s), {warnings} warning(s)")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
