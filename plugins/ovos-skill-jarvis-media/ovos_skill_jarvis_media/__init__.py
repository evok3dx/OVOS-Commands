"""Jarvis Media OVOS skill."""
from __future__ import annotations

import subprocess
import sys
import threading

from ovos_workshop.skills.ovos import OVOSSkill

from .bridge import register, unregister
from .media import control, first_result, normalise_query, open_brave, search_command
from . import pipeline


EVENT_CONTROL = "jarvis.media.control"
EVENT_CANCEL = "jarvis.media.cancel"
EVENT_STATUS = "jarvis.media.status"
REVISION = "jarvis.media.plugin.1"


class JarvisMediaSkill(OVOSSkill):
    """One restricted backend for YouTube requests and MPRIS transport."""

    def initialize(self):
        self._media_lock = threading.RLock()
        self._media_generation = 0
        self._media_process = None
        self.add_event(pipeline.EVENT_PLAY, self._handle_play,
                       handler_info="mycroft.skill.handler", is_intent=True)
        self.add_event(EVENT_CONTROL, self._handle_control)
        self.add_event(EVENT_CANCEL, self._handle_cancel)
        self.add_event(EVENT_STATUS, self._handle_status)
        register(self)
        self.log.info("Jarvis Media ready (%s)", REVISION)

    def _handle_status(self, message):
        self.bus.emit(message.reply(EVENT_STATUS + ".response", {
            "ready": True, "revision": REVISION,
            "pipeline": bool(pipeline.PIPELINE_LOADED),
            "actions": ["play", "pause", "stop", "next", "previous"],
        }))

    def _handle_play(self, message):
        query = normalise_query(message.data.get("query"))
        with self._media_lock:
            self._cancel_locked()
            self._media_generation += 1
            generation = self._media_generation
        threading.Thread(target=self._search_and_open, args=(query, generation),
                         name="jarvis-media-youtube", daemon=True).start()

    def _search_and_open(self, query, generation):
        process = None
        try:
            process = subprocess.Popen(
                search_command(sys.executable, query), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, start_new_session=True,
            )
            with self._media_lock:
                if generation != self._media_generation:
                    process.terminate()
                    return
                self._media_process = process
            stdout, stderr = process.communicate(timeout=30)
            if process.returncode:
                raise RuntimeError((stderr or "YouTube search failed").strip()[-500:])
            url, title = first_result(stdout)
            with self._media_lock:
                if generation != self._media_generation:
                    return
                self._media_process = None
            if not open_brave(url):
                raise RuntimeError("The configured Brave launcher did not start")
            self.log.info("Opened first YouTube result in Brave: %s", title)
        except subprocess.TimeoutExpired:
            if process is not None:
                process.kill()
            self.log.warning("YouTube result search timed out")
            self.speak("YouTube search took too long.")
        except Exception as error:
            self.log.warning("Media request failed: %s", error)
            self.speak("I could not open that on YouTube.")
        finally:
            with self._media_lock:
                if generation == self._media_generation:
                    self._media_process = None

    def _handle_control(self, message):
        action = str(message.data.get("action") or "")
        if action not in {"play", "pause", "stop", "next", "previous"}:
            self.log.warning("Rejected unknown Media action")
            return
        threading.Thread(target=self._control, args=(action,),
                         name="jarvis-media-control", daemon=True).start()

    def _control(self, action):
        try:
            success, player = control(action)
            if success:
                self.log.info("Media action sent%s: %s",
                              " to " + player if player else "", action)
            else:
                self.log.info("Media action ignored; no compatible player: %s", action)
        except FileNotFoundError:
            self.log.error("playerctl is unavailable")
            self.speak("Media control is not installed.")
        except Exception:
            self.log.exception("Media action failed: %s", action)
            self.speak("I could not control media playback.")

    def _handle_cancel(self, _message=None):
        with self._media_lock:
            self._media_generation += 1
            self._cancel_locked()

    def _cancel_locked(self):
        process = self._media_process
        self._media_process = None
        if process is not None and process.poll() is None:
            process.terminate()

    def shutdown(self):
        self._handle_cancel()
        unregister(self)
        return super().shutdown()


def create_skill(bus=None, skill_id=None):
    """Compatibility factory for older OVOS skill loaders."""
    return JarvisMediaSkill(bus=bus, skill_id=skill_id)
