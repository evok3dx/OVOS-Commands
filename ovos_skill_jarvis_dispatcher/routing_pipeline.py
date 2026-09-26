"""Separate command routing from general answers, sharing cancellation and options."""
from ovos_plugin_manager.templates.pipeline import PipelinePlugin, IntentHandlerMatch
from .router_bridge import get_dispatcher
from .routing_runtime import EVENT, REPLY_EVENT
from .routing_model import RequestCancelled
from .routing_chat import question_like

UTTERANCE_EVENTS = frozenset(("recognizer_loop:utterance", "ovos.utterance.handle"))

PIPELINE_LOADED = False
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
        if question_like(text):
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


class JarvisQwenChatPipeline(PipelinePlugin):
    def __init__(self, bus=None, config=None):
        super().__init__(bus, config)
        global CHAT_PIPELINE_LOADED
        CHAT_PIPELINE_LOADED = True

    def match(self, utterances, lang, message):
        skill, runtime = current_runtime(utterances, lang, message)
        if runtime is None:
            return None
        if message.context.get('jarvis_qwen_unavailable'):
            return None
        text = utterances[0]
        try:
            return reply_match(skill, runtime.reply_token(text, message.context.get('jarvis_qwen_epoch', -1),
                                                         command=not question_like(text)), text)
        except Exception as error:
            skill.log.warning('Qwen answer pipeline unavailable (%s)', type(error).__name__)
            return None
