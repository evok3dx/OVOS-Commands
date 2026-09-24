"""Selected, unchanged methods from OpenVoiceOS app launcher 0.13.2a1.

Source: https://github.com/OpenVoiceOS/ovos-skill-application-launcher
Git blob: 58163bee8d8a0b5c1405cb6046d2bb976a4e2d28
Apache-2.0; see OVOS-LAUNCHER-LICENSE.txt and LAUNCHER.md.
Only the imports/class wrapper are local. No voice handlers are registered.
"""
import configparser
import shlex
import subprocess
from os import listdir
from os.path import expanduser, isdir, join
from typing import Dict, List, Union, Generator, Optional
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import LOG
from ovos_utils.parse import match_one


class ApplicationLauncherSkill:
    def launch_app(self, app: str) -> bool:
        """Launch an application by name if a match is found.

        Args:
            app: The name of the application to launch.

        Returns:
            True if the application is launched successfully, False otherwise.
        """
        cmd, score = match_one(app.title(), self.applist)
        if score >= self.settings.get("thresh", 0.85):
            LOG.info(f"Matched application: {app} (command: {cmd})")
            try:
                # Launch the application in a new process without blocking
                subprocess.Popen(shlex.split(cmd), shell=self.settings.get("shell", False))
                self.acknowledge()
                return True
            except Exception as e:
                LOG.error(f"Failed to launch {app}: {e}")
        return False


    @staticmethod
    def parse_desktop_file(file_path: str, extra_langs: Optional[List[str]] = None) -> Dict[str, Union[str, List[str]]]:
        """Parse a .desktop file to extract relevant application metadata.

        Args:
            file_path: Path to the .desktop file.
            extra_langs: List of additional languages to consider.

        Returns:
            A dictionary containing the parsed application metadata.
        """
        extra_langs = extra_langs or []
        extra_langs = [standardize_lang_tag(l) for l in extra_langs]

        config = configparser.ConfigParser(interpolation=None, delimiters=('=', ':'))
        config.optionxform = str  # To keep case-sensitivity of keys
        config.read(file_path)

        data = {}

        LIST_KEYS = ["Categories", "Keywords", "MimeType"]
        LIST_DELIM = ";"
        if 'Desktop Entry' in config:
            keys = config['Desktop Entry'].keys()
            for key in keys:
                v = config['Desktop Entry'].get(key)
                if key in LIST_KEYS:
                    v = [v for v in v.split(LIST_DELIM) if v]

                if "[" in key:
                    raw_lang = key.split("[")[-1].split("]")[0]
                    try:
                        l = standardize_lang_tag(raw_lang)
                    except ValueError:
                        # .desktop files may carry POSIX-style locale modifiers
                        # (e.g. "sr@latn") that are not valid BCP-47 tags; keep
                        # the original key rather than crashing the parser
                        l = raw_lang
                    k = key.split("[")[0]
                    key = f"{k}[{l}]"

                data[key] = v

        keys_of_interest = [
            'Name',
            'GenericName',
            "Categories",
            "Comment",
            'Keywords',
            "Exec",
            "Type",
            #   'MimeType', # for future usage
            'Icon',  # future usage in a UI
            #   'DBusActivatable'  # for future usage instead of subprocess
        ]
        for l in extra_langs:
            keys_of_interest += [f"Name[{l}]", f"GenericName[{l}]", f"Comment[{l}]"]

        return {k: v for k, v in data.items() if k in keys_of_interest}
