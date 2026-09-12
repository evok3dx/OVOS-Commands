import re
import subprocess
from pathlib import Path
from urllib.parse import quote_plus


class BrowserActionsMixin:
    """Allowlisted browser discovery, focus, navigation and search actions."""

    def _active_browser(self):
        """Return the supported browser owning the active window."""

        try:
            window_id = subprocess.run(
                ["/usr/bin/xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            ).stdout.strip()

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

        return browser_was_open

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
        """Capture a browser query in dedicated response mode."""

        query = self.get_response(
            "What should I search for?",
            message=message,
            num_retries=1,
            wait=True
        )

        query = str(query or "").strip()

        cancelled = {
            "cancel",
            "cancel it",
            "never mind",
            "nevermind",
            "stop",
            "wait"
        }

        if not query or query.lower().strip(" .") in cancelled:
            self.speak("Cancelled.")
            return

        self._run_browser_action(
            "search",
            query,
            browser=browser
        )
