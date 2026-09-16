#!/usr/bin/env python3
"""Configure reviewed Jarvis integrations without installing applications."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


capability_module = load_module(
    "jarvis_capabilities", ROOT / "ovos_skill_jarvis_dispatcher/capabilities.py"
)
profile_module = load_module(
    "jarvis_profile", ROOT / "ovos_skill_jarvis_dispatcher/profile.py"
)
INTEGRATIONS = capability_module.INTEGRATIONS
build_configuration = capability_module.build_configuration
detect_applications = capability_module.detect_applications
APPLICATION_INTEGRATIONS = profile_module.APPLICATION_INTEGRATIONS
resolve_profile = profile_module.resolve_profile


def home_path() -> Path:
    return Path(os.environ.get("JARVIS_HOME", Path.home())).expanduser()


def default_output() -> Path:
    return home_path() / ".config/jarvis/capabilities.json"


def display_name(integration: str) -> str:
    definition = APPLICATION_INTEGRATIONS.get(integration, {})
    return str(definition.get("display_name", integration.replace("_", " ").title()))


def atomic_write(path: Path, data: dict[str, object]) -> None:
    resolve_profile(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def migrate_profile(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    applications = dict(raw.get("applications", {}))
    # Older Brain profiles used generic Mail as a Proton alias. Preserve both
    # behaviours while making the generic role follow the OS default.
    if applications.get("mail") == "proton_mail":
        applications["mail"] = "default_mail"
        applications["proton_mail"] = "proton_mail"
    legacy_private = raw.get("private_extensions", {})
    preserve_private_agents = bool(
        isinstance(legacy_private, dict) and legacy_private.get("agents") is True
    ) or raw.get("name") in {"brain", "brain-compatibility"}
    data = {
        "schema_version": 1,
        "name": "jarvis",
        "mode": "migrated",
        "conversation": bool(raw.get("conversation", False)),
        "wake_phrase": str(raw.get("wake_phrase", "hey_jarvis")),
        "applications": applications,
        # This flag is never offered by normal setup. It only preserves an
        # already-customised Brain deployment during migration.
        "private_extensions": {"agents": preserve_private_agents},
    }
    resolve_profile(data)
    return data


def choose_interactively(detected: dict[str, str]) -> tuple[str, set[str]]:
    print("\nJarvis application setup")
    print("No applications will be installed or changed.\n")
    print("1. All detected supported applications")
    print("2. Core voice controls only")
    print("3. Choose applications")
    answer = input("Selection [1]: ").strip() or "1"
    if answer == "1":
        return "all", set()
    if answer == "2":
        return "core", set()
    if answer != "3":
        raise ValueError("Selection must be 1, 2 or 3")
    available = list(detected.values())
    if not available:
        print("No supported applications were detected; using core controls.")
        return "core", set()
    print("\nDetected applications:")
    for index, integration in enumerate(available, 1):
        print(f"{index}. {display_name(integration)}")
    values = input("Numbers separated by commas, or Enter for none: ").strip()
    if not values:
        return "custom", set()
    selected: set[str] = set()
    for value in values.split(","):
        index = int(value.strip())
        if not 1 <= index <= len(available):
            raise ValueError(f"Application number out of range: {index}")
        selected.add(available[index - 1])
    return "custom", selected


def choose_with_gui(detected: dict[str, str]) -> tuple[str, set[str]] | None:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
    except Exception as error:
        raise RuntimeError(f"GTK 3 is unavailable: {error}") from error

    dialog = Gtk.Dialog(title="Jarvis Setup")
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Save", Gtk.ResponseType.OK)
    dialog.set_default_size(430, 320)
    box = dialog.get_content_area()
    box.set_spacing(8)
    intro = Gtk.Label(
        label="Choose what Jarvis should control. No applications will be installed.",
        xalign=0,
    )
    intro.set_line_wrap(True)
    box.pack_start(intro, False, False, 4)

    all_button = Gtk.RadioButton.new_with_label_from_widget(None, "All detected applications")
    core_button = Gtk.RadioButton.new_with_label_from_widget(all_button, "Core controls only")
    custom_button = Gtk.RadioButton.new_with_label_from_widget(all_button, "Choose applications")
    for button in (all_button, core_button, custom_button):
        box.pack_start(button, False, False, 0)

    checks: dict[str, object] = {}
    applications_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    applications_box.set_margin_start(24)
    for integration in detected.values():
        check = Gtk.CheckButton(label=display_name(integration))
        check.set_active(True)
        check.set_sensitive(False)
        checks[integration] = check
        applications_box.pack_start(check, False, False, 0)
    if not checks:
        applications_box.pack_start(
            Gtk.Label(label="No supported applications detected.", xalign=0),
            False, False, 0,
        )
    box.pack_start(applications_box, True, True, 0)

    def update_checks(*_args):
        enabled = custom_button.get_active()
        for check in checks.values():
            check.set_sensitive(enabled)

    custom_button.connect("toggled", update_checks)
    dialog.show_all()
    response = dialog.run()
    if response != Gtk.ResponseType.OK:
        dialog.destroy()
        return None
    if all_button.get_active():
        result = ("all", set())
    elif core_button.get_active():
        result = ("core", set())
    else:
        result = (
            "custom",
            {name for name, check in checks.items() if check.get_active()},
        )
    dialog.destroy()
    return result


def restart_jarvis() -> None:
    restart = shutil.which("jarvis-restart")
    if restart:
        subprocess.run([restart], check=False)
        return
    systemctl = shutil.which("systemctl")
    if systemctl:
        subprocess.run(
            [systemctl, "--user", "restart", "ovos-core.service"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--mode", choices=("all", "core", "custom"))
    result.add_argument("--apps", default="", help="Comma-separated detected integration IDs")
    result.add_argument("--gui", action="store_true")
    result.add_argument("--show", action="store_true")
    result.add_argument("--migrate-profile", type=Path)
    result.add_argument("--output", type=Path, default=default_output())
    result.add_argument("--no-restart", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.apps and args.mode != "custom":
        raise ValueError("--apps requires --mode custom")
    if args.gui and (args.mode or args.apps or args.migrate_profile):
        raise ValueError("--gui cannot be combined with mode or migration options")
    if args.show:
        if not args.output.is_file():
            print("Jarvis has not been configured yet.")
            return 1
        print(args.output.read_text(encoding="utf-8"), end="")
        return 0

    detected = detect_applications(home_path())
    if args.migrate_profile:
        data = migrate_profile(args.migrate_profile)
    else:
        selected = {value.strip() for value in args.apps.split(",") if value.strip()}
        if args.gui:
            choice = choose_with_gui(detected)
            if choice is None:
                return 0
            mode, selected = choice
        elif args.mode:
            mode = args.mode
        elif sys.stdin.isatty():
            mode, selected = choose_interactively(detected)
        else:
            mode = "all"
        data = build_configuration(mode, detected, selected)

    atomic_write(args.output, data)
    enabled = [display_name(value) for value in data["applications"].values()]
    print(f"Saved Jarvis setup: {args.output}")
    print("Enabled: " + (", ".join(enabled) if enabled else "core controls only"))
    if not args.no_restart and args.output == default_output():
        restart_jarvis()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Jarvis setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
