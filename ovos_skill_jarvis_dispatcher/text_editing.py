import subprocess


class TextEditingActionsMixin:
    """Safe, focused-window text selection and editing actions."""

    @staticmethod
    def _focused_window_details():
        window = subprocess.run(
            ["/usr/bin/xdotool", "getactivewindow"],
            capture_output=True, text=True, check=True, timeout=5,
        ).stdout.strip()
        if not window.isdigit():
            raise RuntimeError("No valid focused window")

        window_class = subprocess.run(
            ["/usr/bin/xprop", "-id", window, "WM_CLASS"],
            capture_output=True, text=True, check=False, timeout=5,
        ).stdout.lower()
        return window, window_class

    @staticmethod
    def _is_terminal_window(window_class):
        return any(
            name in window_class
            for name in ("terminal", "konsole", "xterm", "kitty", "alacritty")
        )

    @staticmethod
    def _send_focused_keys(keys):
        subprocess.run(
            ["/usr/bin/xdotool", "key", "--clearmodifiers", keys],
            check=True, timeout=5,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _select_all_text(self):
        try:
            _, window_class = self._focused_window_details()
            keys = "ctrl+shift+a" if self._is_terminal_window(window_class) else "ctrl+a"
            self._send_focused_keys(keys)
        except Exception:
            self.log.exception("Select-all action failed")
            self.speak("I could not select the text.")

    def _delete_selected_text(self):
        try:
            _, window_class = self._focused_window_details()
            if self._is_terminal_window(window_class):
                self.speak("Text deletion is disabled in Terminal.")
                return
            self._send_focused_keys("Delete")
        except Exception:
            self.log.exception("Delete-text action failed")
            self.speak("I could not delete the selected text.")

    def _clear_focused_text(self):
        try:
            original_window, window_class = self._focused_window_details()
            if self._is_terminal_window(window_class):
                self.speak("Clearing text is disabled in Terminal.")
                return

            response = self.get_response(
                "This will clear all text. Should I continue?",
                num_retries=0, wait=True,
            )
            if self._confirmation_token(response) not in {
                "yes", "yeah", "yep", "confirm", "continue", "do it", "clear it",
            }:
                self.speak("Cancelled.")
                return

            current_window, _ = self._focused_window_details()
            if current_window != original_window:
                self.speak("The focused window changed, so I cancelled.")
                return

            self._send_focused_keys("ctrl+a")
            self._send_focused_keys("Delete")
            self.speak("Text cleared.")
        except Exception:
            self.log.exception("Clear-text action failed")
            self.speak("I could not clear the text.")

    def _undo_text_edit(self):
        self._run_safe_text_shortcut("ctrl+z", "undo")

    def _redo_text_edit(self):
        self._run_safe_text_shortcut("ctrl+shift+z", "redo")

    def _copy_selected_text(self):
        try:
            _, window_class = self._focused_window_details()
            keys = "ctrl+shift+c" if self._is_terminal_window(window_class) else "ctrl+c"
            self._send_focused_keys(keys)
        except Exception:
            self.log.exception("Copy-text action failed")
            self.speak("I could not copy the selected text.")

    def _cut_selected_text(self):
        self._run_safe_text_shortcut("ctrl+x", "cut")

    def _paste_text(self):
        self._run_safe_text_shortcut("ctrl+v", "paste")

    def _save_document(self):
        self._run_safe_text_shortcut("ctrl+s", "save")

    def _press_tab(self):
        """Move to the next control in the currently focused window."""
        try:
            self._focused_window_details()
            self._send_focused_keys("Tab")
        except Exception:
            self.log.exception("Tab action failed")
            self.speak("I could not move to the next field.")

    def _press_shift_tab(self):
        """Move to the previous control in the currently focused window."""
        try:
            self._focused_window_details()
            self._send_focused_keys("shift+Tab")
        except Exception:
            self.log.exception("Shift-Tab action failed")
            self.speak("I could not move to the previous field.")

    @staticmethod
    def _cancelled_search(response):
        value = " ".join(str(response or "").lower().split()).strip(" .")
        return not value or value in {
            "cancel", "cancel it", "never mind", "nevermind", "stop", "wait",
        }

    @staticmethod
    def _type_focused_text(text):
        subprocess.run(
            [
                "/usr/bin/xdotool", "type", "--clearmodifiers",
                "--delay", "10", "--", str(text),
            ],
            check=True, timeout=10,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _search_focused_content(self):
        """Open the focused application's local search and enter a query."""
        try:
            original_window, window_class = self._focused_window_details()
            keys = (
                "ctrl+shift+f"
                if self._is_terminal_window(window_class)
                else "ctrl+f"
            )
            self._send_focused_keys(keys)

            response = self.get_response(
                "What should I search for?", num_retries=0, wait=True,
            )
            if self._cancelled_search(response):
                self.speak("Cancelled.")
                return

            current_window, _ = self._focused_window_details()
            if current_window != original_window:
                self.speak("The focused window changed, so I cancelled.")
                return

            self._type_focused_text(response)
        except Exception:
            self.log.exception("Focused-content search failed")
            self.speak("I could not search this window.")

    def _run_safe_text_shortcut(self, keys, action):
        try:
            _, window_class = self._focused_window_details()
            if self._is_terminal_window(window_class):
                self.speak(f"{action.title()} is disabled in Terminal.")
                return
            self._send_focused_keys(keys)
        except Exception:
            self.log.exception(f"{action.title()} action failed")
            self.speak(f"I could not {action} that.")
