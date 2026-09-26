import subprocess
from pathlib import Path


class AgentActionsMixin:
    """Allowlisted Codex and Claude window, message and response actions."""

    AGENT_NAMES = {
        "codex": "Codex agent",
        "claude": "Claude agent",
    }

    def _launch_claude_session_control(self, action: str) -> None:
        """Open a root-validated Claude session action as agent-claude."""
        if action not in {"new", "agents"}:
            raise ValueError("Unsupported Claude session action")

        titles = {
            "new": "New Claude Agent",
            "agents": "Claude Agents",
        }
        try:
            subprocess.Popen(
                [
                    "/usr/bin/gnome-terminal",
                    "--window",
                    f"--title={titles[action]}",
                    "--",
                    "/usr/bin/bash",
                    "-lc",
                    (
                        "exec /usr/bin/sudo -n "
                        "/usr/local/sbin/jarvis-claude-session "
                        f"{action}"
                    ),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            self.log.exception("Claude session control failed")
            self.speak("I could not open the Claude agent session.")

    def _create_claude_subagent(self) -> None:
        """Start a guided, folder-restricted subagent creation conversation."""
        prompt = (
            "Help me create a new custom Claude Code subagent. Before writing "
            "or changing any files, ask me for its purpose, allowed tools, "
            "and the exact folders it may access. Keep it inside this "
            "restricted agent workspace. Do not request access outside "
            "/home/agent-claude/workspace or /srv/agent-inbox/claude."
        )
        self._send_agent_message("claude", prompt)

    def _window_action(self, action: str, agent: str) -> None:
        helper = Path.home() / ".local/bin/jarvis-agent-window"
        display = self.AGENT_NAMES[agent]

        try:
            subprocess.run(
                [str(helper), action, agent],
                check=True,
                timeout=15
            )
        except Exception:
            self.log.exception("Agent window action failed")
            self.speak(f"I could not {action} {display}.")
            return

        responses = {
            "open": f"{display} is ready.",
            "focus": f"Showing {display}.",
            "minimize": f"{display} is minimized.",
            "close": f"{display} is hidden. Its work continues."
        }
        self.speak(responses[action])

    def _send_agent_message(self, agent: str, prompt: str) -> None:
        """Submit a dictated message through the allowlisted agent helper."""

        display = self.AGENT_NAMES[agent]

        try:
            subprocess.run(
                [
                    "/usr/bin/sudo",
                    "-n",
                    "/usr/local/sbin/jarvis-agent-message",
                    agent
                ],
                input=prompt + "\n",
                text=True,
                capture_output=True,
                check=True,
                timeout=20
            )
        except Exception:
            self.log.exception("Agent message failed")
            self.speak(f"I could not message {display}.")
            return

        try:
            subprocess.run(
                [
                    str(Path.home() / ".local/bin/jarvis-agent-window"),
                    "open",
                    agent
                ],
                check=True,
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.log.exception("Agent window display failed")

        self.speak("Message sent.")

    def _read_agent_response(self, agent=None):
        sources = {
            "codex": Path(
                "/var/spool/jarvis-responses/codex/latest.json"
            ),
            "claude": Path(
                "/var/spool/jarvis-responses/claude/latest.json"
            )
        }

        readers = {
            "codex": (
                Path.home() /
                ".local/bin/jarvis-read-codex-response.py"
            ),
            "claude": (
                Path.home() /
                ".local/bin/jarvis-read-claude-response.py"
            )
        }

        if agent is None:
            available = [
                name for name, source in sources.items()
                if source.is_file()
            ]

            if not available:
                self.speak("There is no response to read.")
                return

            agent = max(
                available,
                key=lambda name: sources[name].stat().st_mtime
            )

        if not sources[agent].is_file():
            self.speak(
                f"There is no {self.AGENT_NAMES[agent]} "
                "response to read."
            )
            return

        try:
            subprocess.run(
                [str(readers[agent])],
                check=True,
                timeout=20
            )
        except Exception:
            self.log.exception("Agent response reader failed")
            self.speak(
                f"I could not read the "
                f"{self.AGENT_NAMES[agent]} response."
            )
