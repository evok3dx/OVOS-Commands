"""In-process handoff from bounded classification to existing desktop handlers."""
import copy
import json
import secrets
import threading
import time
import weakref
from pathlib import Path

from .action_registry import router_catalog, dispatch_action
from .routing_model import MODEL, OPTIONS, KEEP_ALIVE, local_json, classify, load_profile, candidates_for
from .router_bridge import register_dispatcher, unregister_dispatcher
from . import routing_chat
from .routing_model import RequestCancelled

EVENT = 'jarvis.qwen.execute'
STATUS = 'jarvis.qwen.status'
REPLY_EVENT = 'jarvis.qwen.reply'


def settings():
    path = Path.home() / '.config/jarvis/router.json'
    if not path.is_file() or path.stat().st_size > 4096:
        return False
    value = json.loads(path.read_text())
    return (value.get('mode') == 'on' and value.get('model') == MODEL
            and value.get('timeout_seconds') == 8)


def fingerprint(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


class RouterRuntime:
    def __init__(self, skill, *, start_keeper=True):
        self.skill = weakref.ref(skill)
        self.flight = threading.Lock()
        self.lock = threading.RLock()
        self.epoch = 0
        self.pending = {}
        self.closed = False
        self.cancel_event = threading.Event()
        self.speaking = False
        self.last_timing = {}
        self.history = []
        self.history_time = 0
        self.last = 'ready'
        self.keeper_stop = threading.Event()
        skill.add_event(EVENT, self.execute, handler_info="mycroft.skill.handler",
                        is_intent=True)
        skill.add_event(REPLY_EVENT, self.reply, handler_info="mycroft.skill.handler",
                        is_intent=True)
        skill.add_event(STATUS, self.status)
        for event in ('mycroft.stop', 'recognizer_loop:record_begin',
                      'recognizer_loop:wakeword', 'ovos.utterance.cancelled'):
            skill.add_event(event, self.cancel)
        register_dispatcher(skill)
        if start_keeper:
            threading.Thread(target=self._keep_model_loaded, daemon=True,
                             name="jarvis-qwen-keepalive").start()

    def _keep_model_loaded(self):
        # Empty-message loads run no generation. Refresh residency because the
        # other local clients can reset expiry or memory pressure can evict it.
        while not self.keeper_stop.is_set():
            try:
                if settings() and self.flight.acquire(blocking=False):
                    try:
                        local_json({"model": MODEL, "messages": [], "stream": False,
                                    "keep_alive": KEEP_ALIVE, "options": OPTIONS.copy()}, 45,
                                   cancel=self.keeper_stop)
                    finally:
                        self.flight.release()
            except Exception:
                pass  # Normal requests retain their own bounded failure path.
            self.keeper_stop.wait(180)

    def cancel(self, _message=None):
        with self.lock:
            self.epoch += 1
            self.cancel_event.set()
            self.cancel_event = threading.Event()
            self.pending.clear()
            if self.speaking:
                skill = self.skill()
                if skill:
                    from ovos_bus_client import Message
                    skill.bus.emit(Message("mycroft.audio.speech.stop"))
                self.speaking = False

    def close(self):
        self.closed = True
        self.keeper_stop.set()
        self.cancel()
        skill = self.skill()
        if skill:
            unregister_dispatcher(skill)

    def status(self, message):
        from .routing_pipeline import PIPELINE_LOADED, CHAT_PIPELINE_LOADED, UTTERANCE_EVENTS
        from ovos_config import Configuration
        from ovos_bus_client.session import SessionManager
        skill = self.skill()
        if skill:
            try:
                pipeline = SessionManager.get(message).pipeline
                enabled = (settings() and 'jarvis-qwen-pipeline' in pipeline
                           and 'jarvis-qwen-chat-pipeline' in pipeline
                           and not Configuration().get('intents', {}).get('persona', {}).get('handle_fallback', True))
            except Exception:
                enabled = False
            skill.bus.emit(message.reply(STATUS + '.response', {
                'ready': not self.closed and bool(PIPELINE_LOADED) and bool(CHAT_PIPELINE_LOADED) and enabled,
                'revision': 'qwen.events.1', 'utterance_events': sorted(UTTERANCE_EVENTS), 'timing_ns': self.last_timing,
                'model': MODEL, 'last_result': self.last,
                'actions': len(router_catalog(skill._jarvis_profile))}))

    @staticmethod
    def busy(skill):
        return bool(skill._message_stage or skill._speech_note_dictating)

    def propose(self, utterance, message=None):
        skill = self.skill()
        # A concurrent router request invalidates earlier work; never queue actions.
        self.cancel()
        if message is not None:
            message.context["jarvis_qwen_epoch"] = self.epoch
        if self.closed or not skill or self.busy(skill) or not settings():
            return None
        if not self.flight.acquire(blocking=False):
            return None
        started = time.monotonic()
        try:
            with self.lock:
                epoch = self.epoch
                cancellation = self.cancel_event
            profile = load_profile()  # strict: a missing/corrupt profile disables AI
            if fingerprint(profile) != fingerprint(skill._jarvis_profile):
                return None  # profile changed; native vocabulary needs a restart
            generation = skill._message_generation
            window = skill._active_window_id()
            catalogue = router_catalog(profile)
            result = classify(utterance, catalogue, profile, timeout=8, cancel=cancellation)
            self.last_timing = result.get("timing_ns", {})
            action = result['actual']
            if action == 'none':
                self.last = 'abstained'
                return None
            proposal = {'action': action, 'utterance': utterance, 'profile': fingerprint(profile),
                        'generation': generation, 'window': window, 'epoch': epoch,
                        'expires': started + 10}
            if not self.valid(proposal, skill):
                self.last = 'cancelled'
                return None
            token = secrets.token_urlsafe(24)
            with self.lock:
                if epoch != self.epoch or self.closed:
                    return None
                self.pending = {token: proposal}
            self.last = 'proposed'
            return token
        finally:
            self.flight.release()

    def valid(self, proposal, skill):
        if (self.closed or not settings() or self.busy(skill)
                or proposal['epoch'] != self.epoch
                or time.monotonic() > proposal['expires']
                or skill._message_generation != proposal['generation']):
            return False
        profile = load_profile()
        if proposal['profile'] != fingerprint(profile) or proposal['profile'] != fingerprint(skill._jarvis_profile):
            return False
        if proposal['action'] not in candidates_for(proposal['utterance'], router_catalog(profile), profile):
            return False
        # All proposals must retain focus; focus-relative actions additionally
        # require a known window. Existing native handlers retain their own guards.
        window = skill._active_window_id()
        if window != proposal['window']:
            return False
        if proposal['action'].startswith(('window.', 'reading.', 'browser.')) and not window:
            return False
        if proposal['action'] in {'browser.back', 'browser.forward', 'browser.new_tab'}:
            if skill._active_browser() not in profile['applications']:
                return False
        return True

    def execute(self, message):
        skill = self.skill()
        token = message.data.get('token')
        if not skill or not isinstance(token, str):
            return
        with self.lock:
            proposal = self.pending.pop(token, None)
        if proposal is None:
            return  # forged/replayed action messages cannot supply actions
        try:
            if not self.valid(proposal, skill):
                self.last = 'cancelled'
                return
            # Handlers receive our original validated text, not substituted bus data.
            safe_message = copy.copy(message)
            safe_message.data = {'utterance': proposal['utterance']}
            invoked = dispatch_action(skill, proposal['action'], safe_message, source='router')
            self.last = 'handler_invoked' if invoked else 'rejected'
            self.history.clear()
            skill.log.info('Qwen router: %s %s', self.last, proposal['action'])
        except Exception as error:
            self.last = 'error'
            skill.log.warning('Qwen dispatch failed (%s)', type(error).__name__)
            skill.speak('I could not complete that command.')

    def reply_token(self, utterance, epoch, *, command=False):
        skill = self.skill()
        if (self.closed or not skill or self.busy(skill) or not settings()
                or not isinstance(utterance, str) or not utterance.strip()):
            return None
        with self.lock:
            token = secrets.token_urlsafe(24)
            kind = 'quiet' if epoch != self.epoch else ('failure' if command else 'chat')
            self.pending[token] = {'kind':kind, 'utterance':utterance, 'epoch':epoch,
                                   'expires':time.monotonic() + 20}
            return token

    def reply(self, message):
        skill = self.skill()
        token = message.data.get('token')
        if not skill or not isinstance(token, str):
            return
        with self.lock:
            proposal = self.pending.pop(token, None)
            cancellation = self.cancel_event
        if (not proposal or proposal.get('kind') not in ('chat', 'failure')
                or proposal['epoch'] != self.epoch or self.closed
                or time.monotonic() > proposal['expires'] or self.busy(skill) or not settings()):
            return
        text = "Please repeat."
        if proposal['kind'] == 'chat' and routing_chat.question_like(proposal['utterance']):
            # An interrupted inference releases its socket and lock promptly.
            # A busy model never creates a queue of spoken answers.
            acquired = self.flight.acquire(timeout=.5)
            if not acquired:
                text = 'Please try again.'
            else:
                try:
                    history = self.history if time.monotonic() - self.history_time < 300 else []
                    text, self.last_timing = routing_chat.answer(proposal['utterance'], cancellation, history=history)
                except RequestCancelled:
                    return
                except Exception as error:
                    text = 'I could not get an answer.'
                    skill.log.warning('Qwen answer unavailable (%s)', type(error).__name__)
                finally:
                    self.flight.release()
        with self.lock:
            if (self.closed or cancellation.is_set() or proposal['epoch'] != self.epoch
                    or self.busy(skill) or not settings()):
                return
            self.speaking = True
            # One complete, length-limited response, not an uncancellable stream
            # of sentences arriving after a newer voice command.
            skill.speak(text)
            if proposal["kind"] == "chat":
                if time.monotonic() - self.history_time >= 300:
                    self.history.clear()
                self.history.extend([{"role":"user", "content":proposal["utterance"]},
                                     {"role":"assistant", "content":text}])
                self.history = self.history[-6:]
                self.history_time = time.monotonic()
            else:
                self.history.clear()
            self.last = 'short_reply'
