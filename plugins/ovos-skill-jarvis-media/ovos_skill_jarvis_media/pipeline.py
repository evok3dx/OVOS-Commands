"""Claim bounded title-play requests before the optional Qwen router."""
from ovos_plugin_manager.templates.pipeline import PipelinePlugin, IntentHandlerMatch

from .bridge import get_skill
from .media import query_from_utterance


EVENT_PLAY = "jarvis.media.play_query"
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
        skill = get_skill()
        if skill is None:
            return None
        query = query_from_utterance(utterances[0])
        if not query:
            return None
        return IntentHandlerMatch(
            match_type=EVENT_PLAY,
            match_data={"query": query},
            skill_id=skill.skill_id,
            utterance=utterances[0],
        )
