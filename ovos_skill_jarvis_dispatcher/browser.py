import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote_plus


class BrowserActionsMixin:
    """Allowlisted browser discovery, focus, navigation and search actions."""

    @staticmethod
    def _active_window_id():
        """Return the active X11 window ID, or an empty string."""

        try:
            return subprocess.run(
                ["/usr/bin/xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            ).stdout.strip()
        except Exception:
            return ""

    def _active_browser(self):
        """Return the supported browser owning the active window."""

        try:
            window_id = self._active_window_id()
            if not window_id:
                return None

            window_class = subprocess.run(
                [
                    "/usr/bin/xprop",
                    "-id",
                    window_id,
                    "WM_CLASS"
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            ).stdout.lower()

            if "firefox" in window_class:
                return "firefox"

            if "brave-browser" in window_class:
                return "brave"

        except Exception:
            self.log.debug(
                "Could not identify the active browser",
                exc_info=True
            )

        return None

    def _active_window_title(self):
        """Return the active window title without exposing other window data."""

        try:
            window_id = subprocess.run(
                ["/usr/bin/xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            ).stdout.strip()
            return subprocess.run(
                [
                    "/usr/bin/xprop", "-id", window_id,
                    "_NET_WM_NAME"
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            ).stdout.lower()
        except Exception:
            return ""

    def _active_tab_is_youtube(self):
        """Return true only when the currently visible browser tab is YouTube."""

        return bool(
            self._active_browser()
            and "youtube" in self._active_window_title()
        )

    def _focus_browser(self, browser):
        """Open or focus a supported browser and report prior state."""

        browser = str(browser or "").lower()

        browser_classes = {
            "brave": "brave-browser.brave-browser",
            "firefox": "navigator.firefox"
        }

        if browser not in browser_classes:
            raise ValueError(
                f"Unsupported browser: {browser}"
            )

        helper = Path.home() / ".local/bin/jarvis-app-window"

        windows = subprocess.run(
            ["/usr/bin/wmctrl", "-lx"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        ).stdout.lower()

        browser_was_open = (
            browser_classes[browser] in windows
        )

        subprocess.run(
            [str(helper), "focus", browser],
            check=True,
            timeout=15,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # wmctrl may return before Cinnamon has actually transferred focus.
        # Do not send a shortcut until the requested browser owns the active
        # window, otherwise it can land in the application underneath it.
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            if self._active_browser() == browser:
                return browser_was_open
            time.sleep(0.1)

        raise RuntimeError(
            f"{browser} did not become the active browser"
        )

    def _run_browser_action(
        self,
        action,
        query=None,
        browser=None
    ):
        """Perform an allowlisted action in a supported browser."""

        commands = {
            "scroll_down": [
                str(Path.home() / ".local/bin/"
                    "jarvis-focused-navigation"),
                "scroll_down"
            ],
            "scroll_up": [
                str(Path.home() / ".local/bin/"
                    "jarvis-focused-navigation"),
                "scroll_up"
            ],
            "page_down": [
                str(Path.home() / ".local/bin/"
                    "jarvis-focused-navigation"),
                "page_down"
            ],
            "page_up": [
                str(Path.home() / ".local/bin/"
                    "jarvis-focused-navigation"),
                "page_up"
            ],
            "top": [
                str(Path.home() / ".local/bin/"
                    "jarvis-focused-navigation"),
                "top"
            ],
            "bottom": [
                str(Path.home() / ".local/bin/"
                    "jarvis-focused-navigation"),
                "bottom"
            ],
            "back": [
                "/usr/bin/xdotool", "key",
                "--clearmodifiers", "alt+Left"
            ],
            "forward": [
                "/usr/bin/xdotool", "key",
                "--clearmodifiers", "alt+Right"
            ],
            "new_tab": [
                "/usr/bin/xdotool", "key",
                "--clearmodifiers", "ctrl+t"
            ],
            "close_tab": [
                "/usr/bin/xdotool", "key",
                "--clearmodifiers", "ctrl+w"
            ],
            "refresh": [
                "/usr/bin/xdotool", "key",
                "--clearmodifiers", "ctrl+r"
            ],
            "address": [
                "/usr/bin/xdotool", "key",
                "--clearmodifiers", "ctrl+l"
            ]
        }

        selected_browser = None

        try:
            focused_window_actions = {
                "scroll_down",
                "scroll_up",
                "page_down",
                "page_up",
                "top",
                "bottom"
            }

            if action in focused_window_actions:
                browser_was_open = None
            else:
                selected_browser = (
                    browser
                    or self._active_browser()
                    or "brave"
                )
                browser_was_open = self._focus_browser(
                    selected_browser
                )

            if action == "search":
                query = str(query or "").strip(" .")

                if not query:
                    self.speak("I did not hear the search.")
                    return

                if len(query) > 500:
                    self.speak("That search is too long.")
                    return

                url = (
                    "https://search.brave.com/search?q="
                    + quote_plus(query)
                )

                if browser_was_open:
                    subprocess.run(
                        [
                            "/usr/bin/xdotool",
                            "key",
                            "--clearmodifiers",
                            "ctrl+t"
                        ],
                        check=True,
                        timeout=5,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                subprocess.run(
                    [
                        "/usr/bin/xdotool",
                        "key",
                        "--clearmodifiers",
                        "ctrl+l"
                    ],
                    check=True,
                    timeout=5,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                subprocess.run(
                    [
                        "/usr/bin/xdotool",
                        "type",
                        "--clearmodifiers",
                        "--delay",
                        "10",
                        "--",
                        url
                    ],
                    check=True,
                    timeout=15,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                subprocess.run(
                    [
                        "/usr/bin/xdotool",
                        "key",
                        "--clearmodifiers",
                        "Return"
                    ],
                    check=True,
                    timeout=5,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                return

            if action == "navigate":
                entry = str(query or "").strip(" .")

                if not entry:
                    self.speak("I did not hear the address.")
                    return

                spoken_target = re.sub(
                    r"\s+dot\s+",
                    ".",
                    entry,
                    flags=re.IGNORECASE
                )
                spoken_target = re.sub(
                    r"\s+slash\s+",
                    "/",
                    spoken_target,
                    flags=re.IGNORECASE
                )

                compact_target = re.sub(
                    r"\s+",
                    "",
                    spoken_target
                )

                is_address = bool(
                    re.match(
                        r"^(?:https?://)?"
                        r"(?:[a-z0-9-]+\.)+[a-z]{2,}"
                        r"(?:[/:?#].*)?$",
                        compact_target,
                        flags=re.IGNORECASE
                    )
                )

                if is_address:
                    url = compact_target
                    if not re.match(
                        r"^https?://",
                        url,
                        flags=re.IGNORECASE
                    ):
                        url = "https://" + url
                else:
                    url = (
                        "https://search.brave.com/search?q="
                        + quote_plus(entry)
                    )

                subprocess.run(
                    [
                        "/usr/bin/xdotool",
                        "key",
                        "--clearmodifiers",
                        "ctrl+l"
                    ],
                    check=True,
                    timeout=10
                )
                subprocess.run(
                    [
                        "/usr/bin/xdotool",
                        "type",
                        "--clearmodifiers",
                        "--delay",
                        "1",
                        url
                    ],
                    check=True,
                    timeout=15
                )
                subprocess.run(
                    [
                        "/usr/bin/xdotool",
                        "key",
                        "--clearmodifiers",
                        "Return"
                    ],
                    check=True,
                    timeout=10
                )

                return

            command = commands.get(action)

            if not command:
                raise ValueError(
                    f"Unsupported browser action: {action}"
                )

            subprocess.run(
                command,
                check=True,
                timeout=10,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        except Exception:
            browser_name = (
                str(selected_browser).capitalize()
                if selected_browser
                else "the active window"
            )
            self.log.exception(
                "%s browser action failed",
                browser_name
            )
            self.speak(
                f"I could not control {browser_name}."
            )

    def _prompt_browser_search(self, message, browser):
        """Expose browser search first, then capture and submit a query."""

        try:
            browser_was_open = self._focus_browser(browser)

            if browser_was_open:
                subprocess.run(
                    [
                        "/usr/bin/xdotool", "key",
                        "--clearmodifiers", "ctrl+t"
                    ],
                    check=True,
                    timeout=5,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            subprocess.run(
                [
                    "/usr/bin/xdotool", "key",
                    "--clearmodifiers", "ctrl+l"
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            target_window = self._active_window_id()
            if not target_window or self._active_browser() != browser:
                raise RuntimeError("Browser search target was not verified")
        except Exception:
            self.log.exception("Could not prepare browser search")
            self.speak(
                f"I could not prepare {str(browser).capitalize()} search."
            )
            return

        # Workshop interprets get_response(dialog=...) as a dialog-file key.
        # Use the existing short converse flow for literal spoken prompts.
        with self._message_lock:
            if self._message_stage:
                self.speak("Please finish or cancel the current request.")
                return
            self._message_stage = ("browser_search_firefox" if browser == "firefox"
                                   else "browser_search")
            self._pending_window_id = target_window
            self._message_retries = 1
        self.activate(duration_minutes=1)
        self.speak("What should I search for?", expect_response=True, wait=True)
        self._arm_message_timeout(20)

    def _submit_prompted_browser_search(self, query, browser, window_id):
        """Submit only into the same browser window prepared for the prompt."""
        query = str(query or "").strip(" .")
        if not query or len(query) > 500:
            self.speak("I could not use that search.")
            return
        url = "https://search.brave.com/search?q=" + quote_plus(query)
        try:
            for action in (
                ("key", "--clearmodifiers", "ctrl+a"),
                ("type", "--clearmodifiers", "--delay", "10", "--", url),
                ("key", "--clearmodifiers", "Return"),
            ):
                if self._active_window_id() != window_id or self._active_browser() != browser:
                    self.speak("The focused window changed, so I cancelled.")
                    return
                subprocess.run(
                    ["/usr/bin/xdotool", *action], check=True, timeout=15,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception:
            self.log.exception("Browser search submission failed")
            self.speak("I could not submit that search.")

    def _open_browser_url(self, url, browser=None):
        """Open an allowlisted URL in a new tab of the chosen browser."""

        selected_browser = (
            browser
            or self._active_browser()
            or "brave"
        )
        browser_was_open = self._focus_browser(selected_browser)

        if browser_was_open:
            subprocess.run(
                [
                    "/usr/bin/xdotool", "key",
                    "--clearmodifiers", "ctrl+t"
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        subprocess.run(
            [
                "/usr/bin/xdotool", "key",
                "--clearmodifiers", "ctrl+l"
            ],
            check=True,
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.run(
            [
                "/usr/bin/xdotool", "type",
                "--clearmodifiers", "--delay", "5",
                "--", url
            ],
            check=True,
            timeout=15,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        subprocess.run(
            [
                "/usr/bin/xdotool", "key",
                "--clearmodifiers", "Return"
            ],
            check=True,
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return selected_browser

    def _prompt_youtube_search(self, message):
        """Open YouTube, expose its search field, then capture the query."""

        try:
            if self._active_tab_is_youtube():
                browser = self._active_browser()
            else:
                browser = self._open_browser_url("https://www.youtube.com")
                time.sleep(2)

            # YouTube's slash shortcut focuses the visible search field.
            subprocess.run(
                [
                    "/usr/bin/xdotool", "key",
                    "--clearmodifiers", "slash"
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            query = self.get_response(
                "What should I search YouTube for?",
                message=message,
                num_retries=1,
                wait=True
            )
            query = str(query or "").strip()

            cancelled = {
                "cancel", "cancel it", "never mind", "nevermind",
                "stop", "wait"
            }
            if not query or query.lower().strip(" .") in cancelled:
                self.speak("Cancelled.")
                return

            if len(query) > 500:
                self.speak("That search is too long.")
                return

            self._focus_browser(browser)
            subprocess.run(
                [
                    "/usr/bin/xdotool", "key",
                    "--clearmodifiers", "slash"
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            subprocess.run(
                [
                    "/usr/bin/xdotool", "key",
                    "--clearmodifiers", "ctrl+a"
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            subprocess.run(
                [
                    "/usr/bin/xdotool", "type",
                    "--clearmodifiers", "--delay", "10",
                    "--", query
                ],
                check=True,
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            subprocess.run(
                [
                    "/usr/bin/xdotool", "key",
                    "--clearmodifiers", "Return"
                ],
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.log.exception("YouTube search failed")
            self.speak("I could not search YouTube.")

    def _open_youtube_shorts(self):
        """Open the YouTube Shorts feed in the active supported browser."""

        try:
            self._open_browser_url("https://www.youtube.com/shorts/")
        except Exception:
            self.log.exception("Could not open YouTube Shorts")
            self.speak("I could not open YouTube Shorts.")
    def _open_fixed_website(self, name, url):
        """Open one reviewed URL with the operating system's default browser."""
        try:
            subprocess.run(
                ["/usr/bin/xdg-open", url], check=True, timeout=10,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self.speak(f"Opening {name} in your browser.")
        except Exception:
            self.log.exception("Could not open fixed website: %s", name)
            self.speak(f"I could not open the {name} website.")
