#!/usr/bin/python3
"""Safely change Jarvis's local OVOS wake phrase."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PRESETS = ("hey jarvis", "hello jarvis", "okay jarvis", "computer")


def home_path() -> Path:
    return Path(os.environ.get("JARVIS_HOME", Path.home())).expanduser()


def validate_spoken_phrase(value: str) -> str:
    phrase = " ".join(value.strip().lower().split())
    words = phrase.split()
    if not 1 <= len(words) <= 4:
        raise ValueError("Use a wake phrase between one and four words.")
    for word in words:
        simplified = word.replace("'", "").replace("-", "")
        if not simplified or not all(character.isalnum() for character in simplified):
            raise ValueError("Use only letters, numbers, apostrophes and hyphens.")
    return phrase


def phrase_identifier(phrase: str) -> str:
    identifier = "_".join(
        "".join(character for character in word if character.isalnum())
        for word in phrase.split()
    )
    if not identifier:
        raise ValueError("The wake phrase does not contain a usable word.")
    return identifier


def atomic_json(path: Path, value: dict[str, object], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".new", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(mode)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def load_configure_module(source_root: Path):
    path = source_root / "scripts/configure-wakeword.py"
    spec = importlib.util.spec_from_file_location("jarvis_configure_wakeword", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_backup(path: Path, backup: Path) -> None:
    backup.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, backup)
        backup.chmod(0o600)
    else:
        backup.with_suffix(backup.suffix + ".missing").touch(mode=0o600)


def restore_backup(path: Path, backup: Path) -> None:
    missing = backup.with_suffix(backup.suffix + ".missing")
    if missing.exists():
        path.unlink(missing_ok=True)
    elif backup.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, path)
        path.chmod(0o600)


def apply_phrase(spoken_phrase: str) -> str:
    phrase = validate_spoken_phrase(spoken_phrase)
    identifier = phrase_identifier(phrase)
    home = home_path()
    source_root = home / ".local/src/ovos-skill-jarvis-dispatcher"
    capabilities_path = home / ".config/jarvis/capabilities.json"
    ovos_config_path = home / ".config/mycroft/mycroft.conf"
    if not capabilities_path.is_file():
        raise RuntimeError("Jarvis capabilities are not installed.")

    capabilities = json.loads(capabilities_path.read_text(encoding="utf-8"))
    if not isinstance(capabilities, dict):
        raise ValueError("Jarvis capabilities must be a JSON object.")
    previous = str(capabilities.get("wake_phrase", "hey_jarvis"))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_root = home / ".local/state/jarvis/config-backups" / f"wake-{stamp}"
    capabilities_backup = backup_root / "capabilities.json"
    ovos_backup = backup_root / "mycroft.conf"
    save_backup(capabilities_path, capabilities_backup)
    save_backup(ovos_config_path, ovos_backup)

    try:
        module = load_configure_module(source_root)
        ovos_config = module.load_config(ovos_config_path)
        module.configure(ovos_config, identifier, phrase, previous)
        module.atomic_write(ovos_config_path, ovos_config)
        capabilities["wake_phrase"] = identifier
        capabilities["wake_phrase_spoken"] = phrase
        atomic_json(capabilities_path, capabilities)
        if os.environ.get("JARVIS_TEST_MODE") != "1":
            subprocess.run(
                ["systemctl", "--user", "restart", "ovos-listener.service"],
                check=True,
                timeout=30,
            )
    except BaseException:
        restore_backup(capabilities_path, capabilities_backup)
        restore_backup(ovos_config_path, ovos_backup)
        raise
    return phrase


def gui_phrase(current: str) -> str | None:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    dialog = Gtk.Dialog(title="Jarvis wake phrase")
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Save", Gtk.ResponseType.OK)
    dialog.set_default_size(390, 150)
    box = dialog.get_content_area()
    box.set_spacing(10)
    box.set_margin_start(14)
    box.set_margin_end(14)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    label = Gtk.Label(
        label="Choose a preset or type a short phrase (one to four words).",
        xalign=0,
    )
    label.set_line_wrap(True)
    box.pack_start(label, False, False, 0)
    choices = Gtk.ComboBoxText.new_with_entry()
    for phrase in PRESETS:
        choices.append_text(phrase)
    entry = choices.get_child()
    entry.set_text(current)
    entry.set_activates_default(True)
    dialog.set_default_response(Gtk.ResponseType.OK)
    box.pack_start(choices, False, False, 0)
    dialog.show_all()
    response = dialog.run()
    value = entry.get_text() if response == Gtk.ResponseType.OK else None
    dialog.destroy()
    return value


def show_message(title: str, message: str, error: bool = False) -> None:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.ERROR if error else Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def current_spoken_phrase() -> str:
    path = home_path() / ".config/jarvis/capabilities.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return str(
            value.get(
                "wake_phrase_spoken",
                str(value.get("wake_phrase", "hey_jarvis")).replace("_", " "),
            )
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return "hey jarvis"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phrase")
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    use_gui = args.gui or args.phrase is None

    phrase = args.phrase
    if use_gui:
        phrase = gui_phrase(current_spoken_phrase())
        if phrase is None:
            return 0
    try:
        applied = apply_phrase(str(phrase))
    except Exception as error:
        if use_gui:
            show_message("Wake phrase not changed", str(error), error=True)
            return 1
        raise
    if use_gui:
        show_message("Wake phrase changed", f'Say “{applied}” to wake Jarvis.')
    else:
        print(f"Wake phrase changed: {applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
