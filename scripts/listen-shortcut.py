#!/usr/bin/env python3
"""Manage Jarvis's Cinnamon listen and microphone-toggle shortcuts."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


PARENT_SCHEMA = "org.cinnamon.desktop.keybindings"
CUSTOM_SCHEMA = "org.cinnamon.desktop.keybindings.custom-keybinding"
LEGACY_LISTEN_ENTRY = "jarvis-listen"
LEGACY_MICROPHONE_ENTRY = "jarvis-microphone-toggle"
LEGACY_ENTRIES = {LEGACY_LISTEN_ENTRY, LEGACY_MICROPHONE_ENTRY}
LISTEN_NAME = "Jarvis Listen"
MICROPHONE_NAME = "Jarvis Microphone Toggle"
DEFAULT_LISTEN_SHORTCUT = "<Super>l"
DEFAULT_MICROPHONE_SHORTCUT = "<Shift><Super>l"
DISABLED = "disabled"
LISTEN_PRESETS = (
    ("Windows + L (default)", DEFAULT_LISTEN_SHORTCUT),
    ("Windows + J", "<Super>j"),
    ("Ctrl + Alt + Space", "<Control><Alt>space"),
    ("Disabled", DISABLED),
)
MICROPHONE_PRESETS = (
    ("Shift + Windows + L (default)", DEFAULT_MICROPHONE_SHORTCUT),
    ("Shift + Windows + M", "<Shift><Super>m"),
    ("Ctrl + Alt + M", "<Control><Alt>m"),
    ("Disabled", DISABLED),
)


def home_path() -> Path:
    return Path(os.environ.get("JARVIS_HOME", Path.home())).expanduser()


def run(*arguments: str) -> str:
    result = subprocess.run(
        ["gsettings", *arguments], text=True, capture_output=True, timeout=15,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"gsettings {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip()


def fixed_schemas() -> list[str]:
    return run("list-schemas").splitlines()


def relocatable_schemas() -> list[str]:
    return run("list-relocatable-schemas").splitlines()


def shortcut_schemas_available() -> bool:
    # Cinnamon's custom-keybinding schema is relocatable, so it is deliberately
    # absent from `gsettings list-schemas` on a real desktop.  It must be
    # queried separately rather than treated as a missing Cinnamon component.
    return (
        PARENT_SCHEMA in fixed_schemas()
        and CUSTOM_SCHEMA in relocatable_schemas()
    )


def parse_array(raw: str) -> list[str] | None:
    value = raw.strip()
    if value.startswith("@as "):
        value = value[4:]
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return None
    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return parsed
    return None


def array_value(values: list[str]) -> str:
    return repr(values)


def string_value(raw: str) -> str:
    try:
        value = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return raw.strip("'\"")
    return value if isinstance(value, str) else ""


def target(entry: str) -> str:
    path = f"/org/cinnamon/desktop/keybindings/custom-keybindings/{entry}/"
    return f"{CUSTOM_SCHEMA}:{path}"


def atomic_json(path: Path, value: dict[str, object]) -> None:
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
        temporary.chmod(0o600)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def binding_schemas() -> list[str]:
    return sorted(
        schema for schema in fixed_schemas()
        if schema.startswith("org.cinnamon.desktop.keybindings")
        and schema != CUSTOM_SCHEMA
    )


def snapshot(path: Path) -> None:
    if not shortcut_schemas_available():
        raise RuntimeError("Cinnamon custom keyboard-shortcut schemas are unavailable.")
    values: dict[str, str] = {}
    for schema in binding_schemas():
        for key in run("list-keys", schema).splitlines():
            raw = run("get", schema, key)
            if parse_array(raw) is not None:
                values[f"{schema}\n{key}"] = raw
    entries = parse_array(run("get", PARENT_SCHEMA, "custom-list")) or []
    for entry in entries:
        entry_target = target(entry)
        for key in ("name", "command", "binding"):
            values[f"{entry_target}\n{key}"] = run("get", entry_target, key)
    atomic_json(path, {"schema_version": 3, "values": values})


def restore_snapshot(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") not in {1, 2, 3} or not isinstance(
        data.get("values"), dict
    ):
        raise ValueError("Unsupported Jarvis keyboard-shortcut snapshot")
    for compound, raw in data["values"].items():
        schema, key = compound.split("\n", 1)
        run("set", schema, key, str(raw))


def normalize(shortcut: str) -> str:
    value = shortcut.strip()
    if value.lower() == DISABLED:
        return DISABLED
    if not re.fullmatch(r"(?:<[A-Za-z]+>)+[A-Za-z0-9_+-]+", value):
        raise ValueError(
            "Use a Cinnamon shortcut such as <Super>l or <Shift><Super>l."
        )
    return value


def same_binding(left: str, right: str) -> bool:
    return left.replace("Primary", "Control").lower() == right.replace(
        "Primary", "Control"
    ).lower()


def state_path() -> Path:
    return home_path() / ".config/jarvis/listen-shortcut.json"


def load_state() -> dict[str, object]:
    path = state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def current_shortcuts() -> tuple[str, str]:
    data = load_state()
    try:
        listen = str(
            data.get("listen_shortcut", data.get("shortcut", DEFAULT_LISTEN_SHORTCUT))
        )
        microphone = str(
            data.get("microphone_shortcut", DEFAULT_MICROPHONE_SHORTCUT)
        )
        return normalize(listen), normalize(microphone)
    except (ValueError, TypeError):
        return DEFAULT_LISTEN_SHORTCUT, DEFAULT_MICROPHONE_SHORTCUT


def entry_role(entry: str) -> str | None:
    if entry == LEGACY_LISTEN_ENTRY:
        return "listen"
    if entry == LEGACY_MICROPHONE_ENTRY:
        return "microphone"
    entry_target = target(entry)
    try:
        name = string_value(run("get", entry_target, "name"))
        command = string_value(run("get", entry_target, "command"))
    except RuntimeError:
        return None
    if name == LISTEN_NAME or command.endswith("/.venvs/ovos/bin/ovos-listen"):
        return "listen"
    if name == MICROPHONE_NAME or command.endswith("/.local/bin/jarvis-mic-toggle"):
        return "microphone"
    return None


def allocate_entries(
    entries: list[str], state: dict[str, object]
) -> tuple[str, str, set[str]]:
    managed = set(LEGACY_ENTRIES)
    selected: dict[str, str] = {}
    for role, key in (
        ("listen", "listen_entry"),
        ("microphone", "microphone_entry"),
    ):
        candidate = state.get(key)
        if isinstance(candidate, str) and candidate in entries:
            managed.add(candidate)
            if re.fullmatch(r"custom\d+", candidate):
                selected[role] = candidate
    for entry in entries:
        role = entry_role(entry)
        if role is None:
            continue
        managed.add(entry)
        if role not in selected and re.fullmatch(r"custom\d+", entry):
            selected[role] = entry
    occupied = set(entries) - managed
    for role in ("listen", "microphone"):
        if role in selected:
            occupied.add(selected[role])
            continue
        index = 0
        while f"custom{index}" in occupied:
            index += 1
        selected[role] = f"custom{index}"
        occupied.add(selected[role])
    managed.update(selected.values())
    return selected["listen"], selected["microphone"], managed


def restore_overrides(state: dict[str, object]) -> None:
    overrides = state.get("overrides", {})
    if not isinstance(overrides, dict):
        return
    for compound, raw in overrides.items():
        schema, key = compound.split("\n", 1)
        run("set", schema, key, str(raw))


def check_collisions(
    listen: str, microphone: str, managed_entries: set[str]
) -> None:
    enabled = [value for value in (listen, microphone) if value != DISABLED]
    if len(enabled) == 2 and same_binding(enabled[0], enabled[1]):
        raise RuntimeError("Listening and microphone toggle cannot use the same shortcut.")
    entries = parse_array(run("get", PARENT_SCHEMA, "custom-list")) or []
    for entry in entries:
        if entry in managed_entries:
            continue
        entry_target = target(entry)
        bindings = parse_array(run("get", entry_target, "binding")) or []
        for shortcut in enabled:
            if any(same_binding(shortcut, binding) for binding in bindings):
                name = string_value(run("get", entry_target, "name")) or entry
                raise RuntimeError(
                    f"{shortcut} is already used by the custom shortcut {name!r}. "
                    "Choose another Jarvis shortcut."
                )


def clear_static_collisions(shortcuts: tuple[str, str]) -> dict[str, str]:
    enabled = [value for value in shortcuts if value != DISABLED]
    changed: dict[str, str] = {}
    for schema in binding_schemas():
        for key in run("list-keys", schema).splitlines():
            raw = run("get", schema, key)
            bindings = parse_array(raw)
            if bindings is None or not any(
                same_binding(shortcut, binding)
                for shortcut in enabled for binding in bindings
            ):
                continue
            filtered = [
                binding for binding in bindings
                if not any(same_binding(shortcut, binding) for shortcut in enabled)
            ]
            if schema.endswith("media-keys") and key == "screensaver" and not filtered:
                filtered = ["<Control><Alt>l"]
            changed[f"{schema}\n{key}"] = raw
            run("set", schema, key, array_value(filtered))
    return changed


def update_capabilities(listen: str, microphone: str) -> None:
    path = home_path() / ".config/jarvis/capabilities.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Jarvis capabilities must be a JSON object")
    data["listen_shortcut"] = listen
    data["microphone_shortcut"] = microphone
    atomic_json(path, data)


def configure_target(target: str, name: str, command: Path, shortcut: str) -> None:
    run("set", target, "name", repr(name))
    run("set", target, "command", repr(str(command)))
    run(
        "set", target, "binding",
        array_value([] if shortcut == DISABLED else [shortcut]),
    )


def apply(
    listen_shortcut: str | None = None,
    microphone_shortcut: str | None = None,
) -> tuple[str, str]:
    current_listen, current_microphone = current_shortcuts()
    listen = normalize(listen_shortcut or current_listen)
    microphone = normalize(microphone_shortcut or current_microphone)
    if not shortcut_schemas_available():
        raise RuntimeError("Cinnamon custom keyboard-shortcut schemas are unavailable.")
    path = state_path()
    previous = load_state()
    if previous:
        restore_overrides(previous)
    entries = parse_array(run("get", PARENT_SCHEMA, "custom-list")) or []
    listen_entry, microphone_entry, managed_entries = allocate_entries(
        entries, previous
    )
    check_collisions(listen, microphone, managed_entries)
    overrides = clear_static_collisions((listen, microphone))

    entries = [
        entry for entry in entries
        if entry not in managed_entries
        or entry in {listen_entry, microphone_entry}
    ]
    for entry in (listen_entry, microphone_entry):
        if entry not in entries:
            entries.append(entry)
    home = home_path()
    # Populate newly allocated customN entries before exposing them through
    # custom-list. Cinnamon reads a new entry as soon as the parent list
    # changes and does not reliably notice fields written afterwards.
    configure_target(
        target(listen_entry), LISTEN_NAME,
        home / ".venvs/ovos/bin/ovos-listen", listen,
    )
    configure_target(
        target(microphone_entry), MICROPHONE_NAME,
        home / ".local/bin/jarvis-mic-toggle", microphone,
    )
    run("set", PARENT_SCHEMA, "custom-list", array_value(entries))
    atomic_json(path, {
        "schema_version": 3,
        "listen_shortcut": listen,
        "microphone_shortcut": microphone,
        "listen_entry": listen_entry,
        "microphone_entry": microphone_entry,
        "overrides": overrides,
    })
    update_capabilities(listen, microphone)
    return listen, microphone


def shortcut_row(box, title: str, presets, current: str):
    from gi.repository import Gtk

    box.pack_start(Gtk.Label(label=title, xalign=0), False, False, 0)
    combo = Gtk.ComboBoxText()
    values = []
    for name, value in presets:
        combo.append(value, name)
        values.append(value)
    combo.append("custom", "Custom Cinnamon shortcut…")
    combo.set_active_id(current if current in values else "custom")
    entry = Gtk.Entry()
    entry.set_placeholder_text("Example: <Shift><Super>k")
    if current not in values:
        entry.set_text(current)
    entry.set_sensitive(combo.get_active_id() == "custom")
    combo.connect(
        "changed", lambda widget: entry.set_sensitive(widget.get_active_id() == "custom")
    )
    box.pack_start(combo, False, False, 0)
    box.pack_start(entry, False, False, 0)
    return combo, entry


def chosen_shortcut(combo, entry) -> str:
    if combo.get_active_id() == "custom":
        return entry.get_text()
    return str(combo.get_active_id())


def gui() -> int:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    current_listen, current_microphone = current_shortcuts()
    dialog = Gtk.Dialog(title="Jarvis keyboard shortcuts")
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Save", Gtk.ResponseType.OK)
    box = dialog.get_content_area()
    box.set_spacing(10)
    box.set_border_width(14)
    label = Gtk.Label(
        label=(
            "Listening starts one manual command. Microphone toggle stops or starts "
            "continuous wake-word listening.\nWith the defaults, Ctrl+Alt+L remains "
            "available for screen lock."
        ),
        xalign=0,
    )
    label.set_line_wrap(True)
    box.pack_start(label, False, False, 0)
    listen_combo, listen_entry = shortcut_row(
        box, "Start listening", LISTEN_PRESETS, current_listen
    )
    microphone_combo, microphone_entry = shortcut_row(
        box, "Toggle microphone", MICROPHONE_PRESETS, current_microphone
    )
    dialog.show_all()
    response = dialog.run()
    listen = chosen_shortcut(listen_combo, listen_entry)
    microphone = chosen_shortcut(microphone_combo, microphone_entry)
    dialog.destroy()
    if response != Gtk.ResponseType.OK:
        return 0
    try:
        applied_listen, applied_microphone = apply(listen, microphone)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        message = Gtk.MessageDialog(
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Could not change the Jarvis shortcuts",
        )
        message.format_secondary_text(str(error))
        message.run()
        message.destroy()
        return 1
    message = Gtk.MessageDialog(
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text="Jarvis keyboard shortcuts saved",
    )
    message.format_secondary_text(
        f"Listen: {applied_listen}\nMicrophone: {applied_microphone}"
    )
    message.run()
    message.destroy()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortcut", dest="listen_shortcut")
    parser.add_argument("--microphone-shortcut")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--restore-snapshot", type=Path)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    actions = sum(bool(value) for value in (args.snapshot, args.restore_snapshot, args.gui))
    if actions > 1:
        parser.error("choose only one of --snapshot, --restore-snapshot or --gui")
    if args.snapshot:
        snapshot(args.snapshot)
    elif args.restore_snapshot:
        restore_snapshot(args.restore_snapshot)
    elif args.gui:
        return gui()
    else:
        listen, microphone = apply(args.listen_shortcut, args.microphone_shortcut)
        print(f"listen={listen}")
        print(f"microphone={microphone}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
