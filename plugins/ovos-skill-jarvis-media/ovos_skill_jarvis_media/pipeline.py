"""Claim bounded title-play requests before the optional Qwen router."""
from ovos_plugin_manager.templates.pipeline import PipelinePlugin, IntentHandlerMatch
from ovos_bus_client.message import Message

from .bridge import get_skill, remote_enabled
from .media import query_from_utterance


EVENT_PLAY = "jarvis.media.play_query"
SKILL_ID = "ovos-skill-jarvis-media.openvoiceos"
UTTERANCE_EVENTS = frozenset(("recognizer_loop:utterance", "ovos.utterance.handle"))
PIPELINE_LOADED = False


class JarvisMediaPipeline(PipelinePlugin):
    def __init__(self, bus=None, config=None):
        super().__init__(bus, config)
        global PIPELINE_LOADED
        PIPELINE_LOADED = True

    def match(self, utterances, lang, message):
        if (message.msg_type not in UTTERANCE_EVENTS
                or not str(lang).lower().startswith("en")
                or not utterances or not isinstance(utterances[0], str)):
            return None
        query = query_from_utterance(utterances[0])
        if not query:
            return None
        skill = get_skill()
        if skill is None:
            if not remote_enabled():
                return None
            # The existing trusted local bus crosses the worker boundary.
            # Never claim a request for a disabled or unavailable helper.
            response = self.bus.wait_for_response(
                Message("jarvis.media.status", context={"source": "skills",
                        "destination": SKILL_ID}), timeout=0.5)
            if (response is None or response.data.get("ready") is not True
                    or response.data.get("revision") != "jarvis.media.plugin.2"
                    or "play" not in response.data.get("actions", [])):
                return None
        return IntentHandlerMatch(
            match_type=EVENT_PLAY,
            # The core dispatcher needs the remote owner's identity to match
            # its framework completion. Keep match.skill_id unset remotely so
            # the automatically unloaded local skill is never activated.
            match_data={"query": query, "skill_id": SKILL_ID},
            # Remote delivery is a fixed pipeline-owned helper event, not an
            # activation of a skill deliberately unloaded from this core.
            skill_id=skill.skill_id if skill is not None else None,
            utterance=utterances[0],
        )
