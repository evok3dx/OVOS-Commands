"""Separate command routing from general answers, sharing cancellation and options."""
from ovos_plugin_manager.templates.pipeline import PipelinePlugin, IntentHandlerMatch
from .router_bridge import get_dispatcher
from .routing_runtime import EVENT, REPLY_EVENT
from .routing_model import RequestCancelled
from .routing_chat import question_like, wake_only, live_question

UTTERANCE_EVENTS = frozenset(("recognizer_loop:utterance", "ovos.utterance.handle"))

PIPELINE_LOADED = False
UNMATCHED_PIPELINE_LOADED = False
CHAT_PIPELINE_LOADED = False


def current_runtime(utterances, lang, message):
    if message.msg_type not in UTTERANCE_EVENTS or not str(lang).lower().startswith('en'):
        return None, None
    if (not utterances or not isinstance(utterances[0], str)
            or not utterances[0].strip()):
        return None, None
    skill = get_dispatcher()
    return skill, getattr(skill, '_qwen_router', None) if skill else None


def reply_match(skill, token, utterance):
    if token:
        return IntentHandlerMatch(match_type=REPLY_EVENT, match_data={'token':token},
                                  skill_id=skill.skill_id, utterance=utterance)


class JarvisQwenPipeline(PipelinePlugin):
    def __init__(self, bus=None, config=None):
        super().__init__(bus, config)
        global PIPELINE_LOADED
        PIPELINE_LOADED = True

    def match(self, utterances, lang, message):
        skill, runtime = current_runtime(utterances, lang, message)
        if runtime is None:
            return None
        text = utterances[0]
        token = runtime.propose_strict(text, message)
        if token:
            return IntentHandlerMatch(match_type=EVENT, match_data={'token': token},
                                      skill_id=skill.skill_id, utterance=text)
        if question_like(text) or wake_only(text) or live_question(text):
            # Let native common-query skills answer questions without a router call.
            runtime.cancel()
            message.context['jarvis_qwen_epoch'] = runtime.epoch
            return None
        try:
            token = runtime.propose(text, message)
            if token:
                return IntentHandlerMatch(match_type=EVENT, match_data={'token':token},
                                          skill_id=skill.skill_id, utterance=text)
        except RequestCancelled:
            runtime.last = 'cancelled'
            return None
        except Exception as error:
            runtime.last = 'unavailable'
            skill.log.warning('Qwen router unavailable (%s)', type(error).__name__)
            message.context['jarvis_qwen_unavailable'] = True
        # Let later native pipelines inspect commands when the local model
        # abstains or times out. The chat fallback handles only unmatched text.
        return None


class JarvisUnmatchedPipeline(PipelinePlugin):
    """Give deterministic feedback before broad fallback skills claim commands."""

    def __init__(self, bus=None, config=None):
        super().__init__(bus, config)
        global UNMATCHED_PIPELINE_LOADED
        UNMATCHED_PIPELINE_LOADED = True

    def match(self, utterances, lang, message):
        skill, runtime = current_runtime(utterances, lang, message)
        if runtime is None:
            return None
        text = utterances[0]
        if question_like(text) or wake_only(text) or live_question(text):
            return None
        return reply_match(skill, runtime.reply_token(
            text, runtime.epoch, command=True), text)


class JarvisQwenChatPipeline(PipelinePlugin):
    def __init__(self, bus=None, config=None):
        super().__init__(bus, config)
        global CHAT_PIPELINE_LOADED
        CHAT_PIPELINE_LOADED = True

    def match(self, utterances, lang, message):
        skill, runtime = current_runtime(utterances, lang, message)
        if runtime is None:
            return None
        text = utterances[0]
        try:
            if wake_only(text):
                # Consume an accidentally repeated wake phrase without speech.
                return reply_match(skill, runtime.reply_token(text, runtime.epoch - 1,
                                                             command=True), text)
            if live_question(text):
                # This stage follows native date/time and common-query stages.
                # If none answered, say Please repeat rather than invent a time.
                return reply_match(skill, runtime.reply_token(text, runtime.epoch,
                                                             command=True), text)
            if message.context.get('jarvis_qwen_unavailable'):
                # A recognised command must not disappear merely because the
                # local router timed out. Empty transcriptions never reach this
                # pipeline, so this remains distinct from a quiet wake.
                return reply_match(skill, runtime.reply_token(text, runtime.epoch,
                                                             command=True), text)
            if not question_like(text):
                # Native handlers and the bounded action router declined this
                # recognised command. Basic failure feedback must not depend
                # on model state or on a context epoch surviving every stage.
                return reply_match(skill, runtime.reply_token(
                    text, runtime.epoch, command=True), text)
            return reply_match(skill, runtime.reply_token(
                text, message.context.get('jarvis_qwen_epoch', -1)), text)
        except Exception as error:
            skill.log.warning('Qwen answer pipeline unavailable (%s)', type(error).__name__)
            return None
