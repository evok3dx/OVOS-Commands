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
import time
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
commands_module = load_module(
    'jarvis_custom_commands', ROOT / 'ovos_skill_jarvis_dispatcher/custom_commands.py')
INTEGRATIONS = capability_module.INTEGRATIONS
build_configuration = capability_module.build_configuration
detect_applications = capability_module.detect_applications
recommended_applications = capability_module.recommended_applications
private_agents_available = capability_module.private_agents_available
APPLICATION_INTEGRATIONS = profile_module.APPLICATION_INTEGRATIONS
resolve_profile = profile_module.resolve_profile


def home_path() -> Path:
    return Path(os.environ.get("JARVIS_HOME", Path.home())).expanduser()


def default_output() -> Path:
    return home_path() / ".config/jarvis/capabilities.json"


DISCOVERED = None


def display_name(integration: str) -> str:
    global DISCOVERED
    if DISCOVERED is None:
        DISCOVERED = profile_module.discovered_applications(home_path())
    definition = APPLICATION_INTEGRATIONS.get(integration, DISCOVERED.get(integration, {}))
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
    # Older reference system profiles used generic Mail as a Proton alias. Preserve both
    # behaviours while making the generic role follow the OS default.
    if applications.get("mail") == "proton_mail":
        applications["mail"] = "default_mail"
        applications["proton_mail"] = "proton_mail"
    legacy_private = raw.get("private_extensions", {})
    preserve_private_agents = bool(
        isinstance(legacy_private, dict) and legacy_private.get("agents") is True
    ) or raw.get("name") in {"reference", "reference-compatibility"}
    wake_phrase = str(raw.get("wake_phrase", "hey_jarvis"))
    data = {
        "schema_version": 1,
        "name": "jarvis",
        "mode": "migrated",
        "conversation": bool(raw.get("conversation", False)),
        "wake_phrase": wake_phrase,
        "wake_phrase_spoken": str(
            raw.get("wake_phrase_spoken", wake_phrase.replace("_", " "))
        ),
        "listen_shortcut": str(raw.get("listen_shortcut", "<Super>l")),
        "microphone_shortcut": str(
            raw.get("microphone_shortcut", "<Shift><Super>l")
        ),
        "applications": applications,
        "default_browser": raw.get("default_browser"),
        "preferred_apps": dict(raw.get("preferred_apps", {})),
        "spoken_names": dict(raw.get("spoken_names", {})),
        # This flag is never offered by normal setup. It only preserves an
        # already-customised reference system deployment during migration.
        "private_extensions": {"agents": preserve_private_agents},
    }
    resolve_profile(data)
    return data


def choose_interactively(detected: dict[str, str]) -> tuple[str, set[str]]:
    print("\nJarvis application setup")
    print("No applications will be installed or changed.\n")
    print("1. Recommended detected applications")
    print("2. All detected supported applications")
    print("3. Choose applications")
    answer = input("Selection [1]: ").strip() or "1"
    if answer == "1":
        return "recommended", set()
    if answer == "2":
        return "all", set()
    if answer != "3":
        raise ValueError("Selection must be 1, 2 or 3")
    available = list(detected.values())
    if not available:
        print("No supported applications were detected; saving an empty custom selection.")
        return "custom", set()
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


def application_rows(detected):
    """One readable name and an actually registered spoken command per app."""
    global DISCOVERED
    if DISCOVERED is None:
        DISCOVERED = profile_module.discovered_applications(home_path())
    rows = []
    for integration in detected.values():
        definition = APPLICATION_INTEGRATIONS.get(integration, DISCOVERED.get(integration, {}))
        name = display_name(integration)
        aliases = definition.get('aliases', [])
        natural = profile_module.discovery.normalise(name)
        role_names = {
            'standard_notes': 'notes', 'proton_mail': 'mail',
            'proton_calendar': 'calendar', 'system_calendar': 'system calendar',
        }
        alias = role_names.get(
            integration, natural if natural in aliases else next(iter(aliases), natural))
        rows.append((integration, name, 'Open ' + alias,
                     'Also: ' + ', '.join('open ' + a for a in aliases if a != alias)))
    return sorted(rows, key=lambda row: row[1].casefold())


def start_save_job(work, finished, schedule):
    """Do disk/service work off the GTK thread; deliver results on that thread."""
    import threading
    def worker():
        try:
            result, error = work(), None
        except Exception as failure:
            result, error = None, str(failure)
        schedule(finished, result, error)
    thread = threading.Thread(target=worker, name='jarvis-save-apps', daemon=False)
    thread.start()
    return thread


def choose_with_gui(detected, existing=None, on_save=None, *, output=None,
                    restart=True, tab='overview', check_only=False):
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GLib, Gdk, Gio
    except Exception as error:
        raise RuntimeError(f'GTK 3 is unavailable: {error}') from error

    class DefaultAppPicker(Gtk.MenuButton):
        """Spacious click-to-open picker for one enabled default app."""

        def __init__(self):
            super().__init__()
            self._active_id = None
            self._choices = {}
            self._group = None
            self._updating = False
            self._changed = None
            self.set_hexpand(True)
            self.set_size_request(360, 42)
            self.set_label('No compatible app enabled')
            self.get_style_context().add_class('jarvis-default-combo')

            self._popover = Gtk.Popover.new(self)
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            outer.set_border_width(7)
            self._choices_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=4)
            self._choices_box.set_size_request(340, 88)
            outer.pack_start(self._choices_box, True, True, 0)
            note = Gtk.Label(label='Enabled compatible applications', xalign=0)
            note.get_style_context().add_class('jarvis-mode-note')
            outer.pack_start(note, False, False, 4)
            self._popover.add(outer)
            self.set_popover(self._popover)

        def connect_changed(self, callback, *args):
            self._changed = (callback, args)

        def remove_all(self):
            for child in self._choices_box.get_children():
                child.destroy()
            self._active_id = None
            self._choices.clear()
            self._group = None
            self.set_label('No compatible app enabled')

        def append(self, identifier, text):
            choice = Gtk.RadioButton.new_with_label_from_widget(self._group, text)
            if self._group is None:
                self._group = choice
            choice.set_size_request(330, 40)
            choice.set_halign(Gtk.Align.FILL)
            choice.get_style_context().add_class('jarvis-default-choice')
            choice.connect('toggled', self._choice_toggled, identifier, text)
            self._choices_box.pack_start(choice, False, False, 0)
            self._choices[identifier] = choice
            choice.show_all()

        def _choice_toggled(self, choice, identifier, text):
            if not choice.get_active():
                return
            self._active_id = identifier
            self.set_label(text)
            if not self._updating and self._changed:
                callback, args = self._changed
                callback(self, *args)
                self._popover.popdown()

        def get_active_id(self):
            return self._active_id

        def set_active_id(self, identifier):
            choice = self._choices.get(identifier)
            if choice is None:
                self.set_active(-1)
                return
            self._updating = True
            try:
                choice.set_active(True)
                self._active_id = identifier
                self.set_label(choice.get_label())
            finally:
                self._updating = False

        def set_active(self, index):
            if index >= 0:
                identifiers = tuple(self._choices)
                if index < len(identifiers):
                    self.set_active_id(identifiers[index])
                    return
            self._updating = True
            try:
                for choice in self._choices.values():
                    choice.set_active(False)
                self._active_id = None
                self.set_label('No compatible app enabled')
            finally:
                self._updating = False

    # One window across tray and legacy shortcuts, using the user's session bus.
    app = None
    if not check_only:
        app = Gtk.Application(application_id='org.jarvis.ControlCenter')
        app.register(None)
        if app.get_is_remote():
            app.activate_action('show', GLib.Variant('s', tab))
            return None
    import importlib.machinery
    editor_path = ROOT / 'command_editor/jarvis-command-editor'
    spec = importlib.util.spec_from_loader('jarvis_command_editor_ui',
        importlib.machinery.SourceFileLoader('jarvis_command_editor_ui', str(editor_path)))
    editor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(editor_module)

    output = output or default_output()
    phrases_path = personal_path()
    expected = {path: path.read_bytes() if path.exists() else None
                for path in (output, phrases_path)}
    definitions = {**APPLICATION_INTEGRATIONS,
                   **profile_module.discovered_applications(home_path())}
    spoken_names = dict((existing or {}).get('spoken_names', {}))
    rows = application_rows(detected)
    recommended = recommended_applications(detected, home_path())
    chosen = (set(existing.get('applications', {}).values())
              if existing else set(recommended))
    state = {'busy': False, 'dirty': False, 'refreshing': False}
    preferred_choices = dict((existing or {}).get('preferred_apps', {}))
    if 'browser' not in preferred_choices and (existing or {}).get('default_browser'):
        preferred_choices['browser'] = existing['default_browser']

    dialog = Gtk.Dialog(title='Configure Jarvis')
    cancel = dialog.add_button('Close', Gtk.ResponseType.CANCEL)
    save = dialog.add_button('Save changes', Gtk.ResponseType.OK)
    save.set_image(Gtk.Image.new_from_icon_name('document-save-symbolic', Gtk.IconSize.BUTTON))
    save.set_always_show_image(True)
    save.get_style_context().add_class('suggested-action')
    dialog.set_resizable(True)
    screen = Gdk.Screen.get_default()
    width, height = (screen.get_width(), screen.get_height()) if screen else (1024, 768)
    dialog.set_default_size(min(860, width - 48), min(740, height - 80))
    dialog.set_size_request(min(520, width - 48), min(380, height - 80))
    dialog.set_position(Gtk.WindowPosition.CENTER)
    outer = dialog.get_content_area()
    outer.set_border_width(12)
    outer.set_spacing(10)
    notebook = Gtk.Notebook()
    outer.pack_start(notebook, True, True, 0)

    def tab_label(label, icon):
        box = Gtk.Box(spacing=6)
        box.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU), False, False, 0)
        box.pack_start(Gtk.Label(label=label), False, False, 0)
        box.show_all()
        return box

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_border_width(12)
    notebook.append_page(box, tab_label('Applications', 'applications-other-symbolic'))
    intro = Gtk.Label(label='Choose which installed apps Jarvis can control. Nothing here installs or removes an app.', xalign=0)
    intro.set_line_wrap(True)
    box.pack_start(intro, False, False, 0)
    all_button = Gtk.RadioButton.new_with_label_from_widget(None, 'All detected')
    recommended_button = Gtk.RadioButton.new_with_label_from_widget(
        all_button, 'Recommended')
    custom_button = Gtk.RadioButton.new_with_label_from_widget(all_button, 'Custom')
    modes = Gtk.Grid(column_spacing=8,row_spacing=8,column_homogeneous=True)
    for index,button in enumerate((recommended_button, all_button, custom_button)):
        button.set_mode(False);button.get_style_context().add_class('jarvis-mode')
        modes.attach(button,index,0,1,1)
    box.pack_start(modes, False, False, 0)
    mode_note = Gtk.Label(xalign=0);mode_note.set_line_wrap(True)
    mode_note.get_style_context().add_class('jarvis-mode-note')
    box.pack_start(mode_note,False,False,0)
    toolbar=Gtk.Box(spacing=10)
    search = Gtk.SearchEntry()
    search.set_placeholder_text('Find an app or spoken command')
    toolbar.pack_start(search,True,True,0)
    count = Gtk.Label(xalign=1)
    toolbar.pack_end(count,False,False,0);box.pack_start(toolbar,False,False,0)

    # Enabled, ID, display name, example, aliases, editable override, GIcon.
    store = Gtk.ListStore(bool, str, str, str, str, str, Gio.Icon)
    icon_defaults = {'files': ('system-file-manager',), 'calculator': ('accessories-calculator',),
        'settings': ('preferences-system',), 'terminal': ('utilities-terminal',),
        'default_mail': ('internet-mail',),
        'proton_mail': ('proton-mail', 'me.proton.Mail', 'internet-mail'),
        'proton_calendar': ('proton-calendar', 'x-office-calendar'),
        'system_calendar': ('org.gnome.Calendar', 'x-office-calendar'),
        'standard_notes': ('standard-notes', 'org.standardnotes.standardnotes', 'accessories-text-editor'),
        'hermes_desktop': ('hermes', 'applications-internet'),
        'claude_desktop': ('com.anthropic.Claude', 'applications-internet'),
        'onlyoffice': ('onlyoffice-desktopeditors', 'x-office-document'),
        'brave': ('brave-browser',), 'firefox': ('firefox',),
        'signal': ('signal-desktop',), 'zoom': ('Zoom', 'zoom')}
    theme = Gtk.IconTheme.get_default()
    menu_entries=profile_module.discovery.scan_desktop_apps(home_path())
    icon_needles={
        'standard_notes': ('standard notes','standardnotes'),
        'proton_mail': ('proton mail','proton-mail'),
        'proton_calendar': ('proton calendar','calendar.proton.me'),
        'hermes_desktop': ('hermes',),
        'claude_desktop': ('claude',),
    }
    def app_icon(key):
        value = definitions.get(key, {}).get('icon', '')
        if not value and key in icon_needles:
            for entry in menu_entries.values():
                identity=' '.join((entry.get('display_name',''),entry.get('desktop_id',''),entry.get('exec',''))).casefold()
                if any(needle in identity for needle in icon_needles[key]) and entry.get('icon'):
                    value=entry['icon'];break
        if not value:value=icon_defaults.get(key, '')
        if isinstance(value, str) and value.startswith('/') and Path(value).is_file():
            return Gio.FileIcon.new(Gio.File.new_for_path(value))
        candidates = (value,) if isinstance(value, str) else tuple(value)
        selected = next((name for name in candidates if name and theme.has_icon(name)), '')
        return Gio.ThemedIcon.new(selected or 'application-x-executable')

    for integration, name, example, alternatives in rows:
        override = spoken_names.get(integration, '')
        store.append([integration in chosen, integration, name,
                      'Open ' + override if override else example, alternatives,
                      override, app_icon(integration)])
    filtered = store.filter_new()
    filtered.set_visible_func(lambda model, itr, _data: search.get_text().casefold() in
                              ' '.join(model[itr][i] for i in (2, 3, 4, 5)).casefold())
    tree = Gtk.TreeView(model=filtered)
    tree.set_headers_visible(True)
    tree.set_enable_search(False)
    tree.set_tooltip_column(4)
    tree.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)
    toggle = Gtk.CellRendererToggle()
    toggle.set_property('ypad', 8)
    tree.append_column(Gtk.TreeViewColumn('Use', toggle, active=0))
    app_column = Gtk.TreeViewColumn('Application')
    pix = Gtk.CellRendererPixbuf()
    app_column.pack_start(pix, False)
    app_column.add_attribute(pix, 'gicon', 6)
    label = Gtk.CellRendererText()
    app_column.pack_start(label, True)
    app_column.add_attribute(label, 'text', 2)
    app_column.set_resizable(True)
    app_column.set_min_width(190)
    tree.append_column(app_column)
    name_renderer = Gtk.CellRendererText()
    name_renderer.set_property('editable', True)
    name_renderer.set_property('ypad', 8)
    name_column = Gtk.TreeViewColumn('Spoken name (edit)', name_renderer, text=5)
    name_column.set_resizable(True)
    name_column.set_min_width(150)
    tree.append_column(name_column)
    example_column = Gtk.TreeViewColumn('Say this', Gtk.CellRendererText(), text=3)
    example_column.set_resizable(True)
    example_column.set_expand(True)
    tree.append_column(example_column)
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scroll.set_shadow_type(Gtk.ShadowType.IN)
    scroll.set_min_content_height(390)
    scroll.add(tree)
    box.pack_start(scroll, True, True, 0)
    help_text = Gtk.Label(label='Optional: edit a spoken name. Leave it blank to keep the app’s normal names.', xalign=0)
    help_text.set_line_wrap(True)
    box.pack_start(help_text, False, False, 0)

    defaults_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    defaults_box.set_border_width(16)
    notebook.append_page(defaults_box, tab_label('Defaults', 'emblem-default-symbolic'))
    defaults_intro = Gtk.Label(
        label='These friendly names keep everyday commands simple. Only enabled, detected apps are used.',
        xalign=0)
    defaults_intro.set_line_wrap(True);defaults_box.pack_start(defaults_intro,False,False,0)
    role_titles = {
        'browser': 'Web browser', 'notes': 'Notes', 'mail': 'Mail',
        'calendar': 'Calendar', 'office': 'Office',
    }
    role_combos = {}
    role_models = {}
    defaults_grid = Gtk.Grid(column_spacing=24, row_spacing=14)
    defaults_grid.set_column_homogeneous(False)
    defaults_grid.set_hexpand(True)
    defaults_box.pack_start(defaults_grid, False, False, 0)
    for index, (role, title) in enumerate(role_titles.items()):
        role_label = Gtk.Label(label=title, xalign=0)
        role_label.set_size_request(150, -1)
        role_label.get_style_context().add_class('jarvis-default-label')
        combo = DefaultAppPicker()
        combo.set_tooltip_text(f'Choose the enabled application used for “open {role}”.')
        defaults_grid.attach(role_label, 0, index, 1, 1)
        defaults_grid.attach(combo, 1, index, 1, 1)
        role_combos[role] = combo
    defaults_box.pack_start(Gtk.Label(
        label='Examples: “open browser”, “open notes”, “open mail”, “open calendar” and “open office”. '
              'Only compatible enabled applications appear here.',
        xalign=0),False,False,0)

    def selection():
        return ('all', set()) if all_button.get_active() else (
            ('recommended', set()) if recommended_button.get_active() else (
            'custom', set(chosen)))

    def prospective():
        mode, selected = selection()
        data=configuration_data(mode, selected, detected, existing, spoken_names)
        applications = data.get('applications', {})
        selected_preferences = {
            role: key for role, key in preferred_choices.items()
            if key in applications
        }
        data['preferred_apps'] = selected_preferences
        selected_browser = selected_preferences.get('browser')
        if selected_browser in {'brave', 'firefox'}:
            data['default_browser'] = selected_browser
        return data

    mode = existing.get('mode', 'custom') if existing else 'recommended'
    (all_button if mode == 'all-detected' else
     recommended_button if mode in {'recommended', 'core-only'} else
     custom_button).set_active(True)
    initial_profile = resolve_profile(prospective())
    editor = editor_module.CommandEditor(profile=initial_profile)
    # Scroll the whole panel too, so all controls remain reachable on small screens.
    command_scroll = Gtk.ScrolledWindow()
    command_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    editor.set_border_width(12)
    command_scroll.add(editor)
    notebook.append_page(command_scroll, tab_label('Custom commands', 'input-keyboard-symbolic'))

    footer = Gtk.Box(spacing=8)
    spinner = Gtk.Spinner()
    footer.pack_start(spinner, False, False, 0)
    status = Gtk.Label(label='Save applies both tabs and briefly restarts voice control.', xalign=0)
    status.set_line_wrap(True)
    status.set_max_width_chars(80)
    footer.pack_start(status, True, True, 0)
    outer.pack_start(footer, False, False, 0)

    def refresh(*_args):
        custom = custom_button.get_active()
        toggle.set_property('activatable', custom and not state['busy'])
        enabled = 0
        for row in store:
            row[0] = (all_button.get_active()
                      or (recommended_button.get_active() and row[1] in recommended)
                      or (custom and row[1] in chosen))
            enabled += int(row[0])
        count.set_text(f'{len(store)} applications · {enabled} enabled')
        preview = prospective()
        resolved_preview = resolve_profile(preview)
        applications = resolved_preview.get('applications', {})
        state['refreshing'] = True
        try:
            for role, combo in role_combos.items():
                candidates = tuple(profile_module.preferred_app_candidates(
                    applications, role))
                if role_models.get(role) != candidates:
                    combo.remove_all()
                    for key in candidates:
                        combo.append(key, applications[key]['display_name'])
                    role_models[role] = candidates
                selected = preferred_choices.get(role)
                if selected not in candidates:
                    selected = resolved_preview.get('preferred_apps', {}).get(role)
                if selected in candidates:
                    preferred_choices[role] = selected
                    combo.set_active_id(selected)
                else:
                    preferred_choices.pop(role, None)
                    combo.set_active(-1)
                combo.set_sensitive(bool(candidates) and not state['busy'])
        finally:
            state['refreshing'] = False
        mode_note.set_text(
            'Best for most people. Includes detected Standard Notes, Proton Mail, Proton Calendar and System Calendar.'
            if recommended_button.get_active() else
            'Enables every detected app in the list, including system utilities.'
            if all_button.get_active() else
            'Tick only the apps you want Jarvis to control.'
        )
        filtered.refilter()

    def changed(*_args):
        state['dirty'] = True
        refresh()

    def toggled(_renderer, path):
        if state['busy'] or not custom_button.get_active():
            return
        key = filtered[Gtk.TreePath.new_from_string(path)][1]
        chosen.symmetric_difference_update({key})
        changed()

    def name_edited(_renderer, path, text):
        if state['busy']:
            return
        row = filtered[Gtk.TreePath.new_from_string(path)]
        key = row[1]
        candidate = dict(spoken_names)
        candidate[key] = text
        try:
            candidate = profile_module.validate_spoken_names(candidate, definitions)
            mode, selected = selection()
            data = configuration_data(mode, selected, detected, existing, candidate)
            validate_configuration(data, editor.mapping)
        except ValueError as error:
            status.set_text(str(error))
            return
        spoken_names.clear()
        spoken_names.update(candidate)
        row[5] = candidate.get(key, '')
        row[3] = 'Open ' + candidate[key] if key in candidate else next(r[2] for r in rows if r[0] == key)
        status.set_text('Name updated. Save changes to activate it.')
        changed()

    name_renderer.connect('edited', name_edited)
    toggle.connect('toggled', toggled)
    for button in (recommended_button, all_button, custom_button):
        button.connect('toggled', changed)
    def preferred_changed(combo, role):
        if state['refreshing']:
            return
        selected = combo.get_active_id()
        if selected:
            preferred_choices[role] = selected
        else:
            preferred_choices.pop(role, None)
        changed()

    for role, combo in role_combos.items():
        combo.connect_changed(preferred_changed, role)
    search.connect('search-changed', lambda *_args: filtered.refilter())
    def switched(_notebook, _page, page_number):
        if page_number == 2:
            editor.refresh_profile(resolve_profile(prospective()))
    notebook.connect('switch-page', switched)
    refresh()
    dialog.connect('delete-event', lambda *_args: state['busy'])

    def finished(result, error):
        state['busy'] = False
        spinner.stop()
        notebook.set_sensitive(True)
        save.set_sensitive(True)
        cancel.set_sensitive(True)
        if not error:
            state['dirty'] = editor.dirty = False
            status.set_text(result)
        else:
            status.set_text('Could not finish applying changes: ' + error)
        refresh()
        return False

    def refresh_voice_config():
        current = json.loads(output.read_text()) if output.is_file() else {}
        if existing is not None:
            existing.clear()
            existing.update(current)
        expected[output] = output.read_bytes() if output.exists() else None

    scripts_path = str(ROOT / 'scripts')
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    from control_center import ControlCenter
    from control_runtime import save_with_lock
    centre = ControlCenter(dialog, outer, notebook, footer, save, cancel,
                           state, editor, refresh_voice_config, check_only=check_only)
    if app is not None:
        show = Gio.SimpleAction.new('show', GLib.VariantType.new('s'))
        show.connect('activate', lambda _action, value: centre.show_tab(value.get_string()))
        app.add_action(show)
        app.connect('activate', lambda _app: centre.show_tab('overview'))
    if check_only:
        # Construct the actual widgets and refresh both tabs on the host. Do not
        # display a window, save settings, restart services or launch apps.
        editor.refresh_profile(resolve_profile(prospective()))
        dialog.destroy()
        print('PASS: Jarvis window, five sections and existing apps/commands initialise.')
        return None
    dialog.show_all()
    centre.show_tab(tab)
    while True:
        response = dialog.run()
        if state['busy']:
            continue
        if response != Gtk.ResponseType.OK:
            if state['dirty'] or editor.dirty:
                question = Gtk.MessageDialog(transient_for=dialog, modal=True,
                    message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE,
                    text='Discard unsaved changes?')
                question.add_button('Keep editing', Gtk.ResponseType.CANCEL)
                question.add_button('Discard', Gtk.ResponseType.OK)
                answer = question.run()
                question.destroy()
                if answer != Gtk.ResponseType.OK:
                    continue
            dialog.destroy()
            return None
        try:
            data = prospective()
            mapping = validate_configuration(data, dict(editor.mapping))
        except ValueError as error:
            status.set_text(str(error))
            continue
        state['busy'] = True
        notebook.set_sensitive(False)
        save.set_sensitive(False)
        cancel.set_sensitive(False)
        status.set_text('Applying changes… Voice control may briefly restart.')
        spinner.start()
        # Immutable snapshots: the worker never reads GTK widgets.
        start_save_job(lambda data=data, mapping=mapping: save_with_lock(lambda: save_configuration(
            data, mapping, output, phrases_path, expected, restart=restart)), finished, GLib.idle_add)


def personal_path():
    return Path(os.environ.get('JARVIS_CUSTOM_COMMANDS_PATH',
                str(home_path() / '.config/jarvis/custom-commands.json')))


def preserve_machine_settings(data, previous):
    """Preserve host-owned settings while applying a new app selection."""
    if previous is None:
        return data
    generated_preferred = dict(data.get('preferred_apps', {}))
    previous_preferred = previous.get('preferred_apps', {})
    if not isinstance(previous_preferred, dict):
        previous_preferred = {}
    merged = {
        **data, **previous,
        'mode': data['mode'],
        'applications': data['applications'],
        'preferred_apps': {**generated_preferred, **previous_preferred},
    }
    return merged


def configuration_data(mode, selected, detected, previous, spoken_names):
    data = build_configuration(
        mode, detected, selected,
        private_agents=private_agents_available(home_path()), home=home_path(),
    )
    data = preserve_machine_settings(data, previous)
    names = profile_module.validate_spoken_names(spoken_names)
    if names or 'spoken_names' in data:
        data['spoken_names'] = names
    return data


def validate_configuration(data, mapping):
    definitions = {**APPLICATION_INTEGRATIONS, **profile_module.discovered_applications(home_path())}
    profile_module.validate_spoken_names(data.get('spoken_names', {}), definitions)
    selected = resolve_profile(data)
    # Compare generated phrases with built-in actions before applying overrides.
    # Covers names such as "a new tab", which would steal "open a new tab".
    raw = {**data, 'spoken_names': {}, 'applications': {
        **{next(category for category, values in profile_module.CATEGORY_INTEGRATIONS.items()
                if integration in values and (category != 'mail' or integration == 'default_mail')): integration
           for integration in APPLICATION_INTEGRATIONS},
        **{key:key for key in definitions if key.startswith('desktop_')}}}
    base = resolve_profile(raw)
    owners = {}
    for action, phrases in commands_module.collect_builtin_inventory(base).items():
        for phrase in phrases:
            owners.setdefault(phrase, set()).add(action)
    expanded = commands_module.collect_builtin_inventory(
        resolve_profile({**raw, 'spoken_names': data.get('spoken_names', {})}))
    original = commands_module.collect_builtin_inventory(base)
    for action, phrases in expanded.items():
        if not action.startswith('application.'):
            continue
        for phrase in phrases:
            conflicts = owners.get(phrase, set()) - {action}
            if conflicts and phrase not in original.get(action, ()):
                raise ValueError(f'Name conflicts with an existing command: “{phrase}”')
    return commands_module.validate_mapping(mapping, profile=selected,
                    builtin_phrases=commands_module.collect_builtin_phrases(selected))


def save_configuration(data, mapping, output, phrases_path, expected, restart=True):
    """Validate both tabs, then save together; recover if either write fails."""
    import fcntl
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output.parent / '.configure.lock'
    with lock_path.open('a') as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = {p: p.read_bytes() if p.exists() else None for p in (output, phrases_path)}
        if before != expected:
            raise ValueError('Settings changed elsewhere. Close and reopen Configure Jarvis before saving.')
        mapping = validate_configuration(data, mapping)
        previous = json.loads(before[output]) if before[output] else None
        old_mapping = json.loads(before[phrases_path]).get('phrases', {}) if before[phrases_path] else {}
        if previous == data and old_mapping == mapping:
            return 'No changes to save.'
        changed = []
        try:
            if previous != data:
                atomic_write(output, data)
                changed.append(output)
            if old_mapping != mapping:
                commands_module.write_mapping(mapping, path=phrases_path, profile=resolve_profile(data),
                    builtin_phrases=commands_module.collect_builtin_phrases(resolve_profile(data)))
                changed.append(phrases_path)
        except Exception:
            for path in reversed(changed):
                if before[path] is None:
                    path.unlink(missing_ok=True)
                else:
                    # Roll back only files successfully changed by this save.
                    fd, tmp = tempfile.mkstemp(prefix='.configure-restore-', dir=path.parent)
                    try:
                        with os.fdopen(fd, 'wb') as stream:
                            stream.write(before[path])
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.chmod(tmp, 0o600)
                        os.replace(tmp, path)
                    finally:
                        if os.path.exists(tmp): os.unlink(tmp)
            raise
        expected.update({p: p.read_bytes() if p.exists() else None for p in before})
    if restart:
        try:
            running = restart_jarvis()
        except Exception as error:
            raise RuntimeError('Settings were saved, but voice restart failed. '
                               'Use Restart Voice System in the tray. ' + str(error)) from error
        return 'Saved. Jarvis is ready.' if running else 'Saved. Start Jarvis from the tray when ready.'
    return 'Saved.'

def save_selection(mode, selected, detected, output, restart=True):
    previous = json.loads(output.read_text()) if output.is_file() else None
    data = build_configuration(mode, detected, selected)
    data = preserve_machine_settings(data, previous)
    if data == previous:
        return 'No changes to save.'
    atomic_write(output, data)
    if restart:
        try:
            running = restart_jarvis()
        except Exception as error:
            raise RuntimeError('App choices were saved, but voice restart failed. '
                               'Use Restart in the tray. ' + str(error)) from error
        return 'Saved. Jarvis is ready.' if running else 'Saved. Start Jarvis from the tray when ready.'
    return 'Saved.'


def restart_jarvis() -> None:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        raise RuntimeError('systemctl is unavailable; restart Jarvis from the tray')
    units = ('ovos-audio.service', 'ovos-core.service', 'ovos-listener.service')
    def state(unit):
        out = subprocess.run([systemctl, '--user', 'show', unit,
            '--property=ActiveState,Requires,BindsTo,PartOf,InvocationID'],
            capture_output=True, text=True, timeout=10, check=True).stdout
        return dict(line.split('=',1) for line in out.splitlines() if '=' in line)
    before = {unit:state(unit) for unit in units}
    active = [unit for unit in units if before[unit].get('ActiveState') == 'active']
    if 'ovos-core.service' not in active:
        return False
    try:
        subprocess.run([systemctl, '--user', 'restart', 'ovos-core.service'],
                       check=True, timeout=60)
    finally:
        # Core may stop listener/audio through systemd dependency relationships.
        for unit in active:
            subprocess.run([systemctl, '--user', 'start', unit], check=True, timeout=60)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        ready = True
        for unit in active:
            current = state(unit)
            ready = ready and current.get('ActiveState') == 'active'
            marker = {'ovos-core.service': 'Jarvis configuration ready',
                      'ovos-listener.service': 'DinkumVoiceService is ready.'}.get(unit)
            if marker:
                invocation = current.get('InvocationID')
                if not invocation:
                    ready = False
                    continue
                logs = subprocess.run(['journalctl', '--user', '-u', unit,
                    '_SYSTEMD_INVOCATION_ID=' + invocation, '--no-pager', '-o', 'cat'],
                    capture_output=True, text=True, check=True, timeout=10).stdout
                ready = ready and marker in logs
        if ready and all(state(u).get('ActiveState') == 'active' for u in active):
            return True
        time.sleep(0.5)
    raise RuntimeError('Settings saved, but voice readiness was not confirmed; check the tray')


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--mode", choices=("recommended", "all", "custom"))
    result.add_argument("--apps", default="", help="Comma-separated detected integration IDs")
    result.add_argument("--gui", action="store_true")
    result.add_argument("--tab", choices=("overview", "applications", "commands", "voice", "updates", "maintenance"), default="overview")
    result.add_argument("--show", action="store_true")
    result.add_argument("--check-gui", action="store_true", help=argparse.SUPPRESS)
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
    existing = json.loads(args.output.read_text()) if args.output.is_file() else None
    if existing is not None:
        # Keep configured specialised integrations available even when their
        # custom installation is not recognised by the detector today.
        for category, integration in existing.get('applications', {}).items():
            if integration in profile_module.CATEGORY_INTEGRATIONS.get(category, set()):
                detected.setdefault(category, integration)
    if args.migrate_profile:
        data = migrate_profile(args.migrate_profile)
    else:
        selected = {value.strip() for value in args.apps.split(",") if value.strip()}
        if args.gui:
            choose_with_gui(detected, existing, output=args.output, tab=args.tab,
                restart=not args.no_restart and args.output == default_output(), check_only=args.check_gui)
            return 0
        elif args.mode:
            mode = args.mode
        elif sys.stdin.isatty():
            mode, selected = choose_interactively(detected)
        else:
            mode = "recommended"
        data = build_configuration(
            mode, detected, selected,
            private_agents=private_agents_available(home_path()), home=home_path(),
        )
        # App selection must not reset conversation, shortcuts, wake phrase,
        # private extensions or other unrelated settings. Keep explicit
        # compatible preferred apps while filling defaults for newly enabled
        # roles.
        data = preserve_machine_settings(data, existing)

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
