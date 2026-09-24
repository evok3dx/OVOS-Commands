"""Short, cancellable general answers using the router's exact runner settings."""
import re
from .routing_model import MODEL, OPTIONS, KEEP_ALIVE, local_json

PROMPT = (
    'You are Jarvis, a private local voice assistant. Give a direct answer in '
    'plain spoken English. Use one short sentence, at most 30 words. If explicitly '
    'asked for detail, use at most three short sentences and 75 words. '
    'No markdown, lists, emojis, filler, follow-up questions or explanations of '
    'your limitations. You answer questions; another component handles desktop '
    'commands. Never claim you performed an action. You have no live data or '
    'web access in this request. Never invent current weather, times, prices or '
    'news. For unavailable live information say: I could not retrieve that live information.'
)


def question_like(text):
    """Broad question/chitchat forms only; never used to authorise an action."""
    text = re.sub(r'[^\w\s]', ' ', text.casefold()).strip()
    text = re.sub(r'\s+', ' ', text)
    return bool(re.match(
        r'^(?:(?:please )?(?:what|why|how|who|where|when|which|whose)\b'
        r'|(?:is|are|was|were|does|do|did|has|have|will|should)\b'
        r'|(?:can|could|would) (?!you\b)'
        r'|(?:please )?(?:explain|describe|define|compare|summarise|summarize)\b'
        r'|(?:please )?tell me (?:about|why|how|what|a joke|a story)\b'
        r'|(?:can|could|would) you (?:please )?(?:explain|describe|define|compare|tell me|summarise|summarize)\b'
        r'|and (?:why|how|what|where|when)\b'
        r'|(?:hello|hi|hey jarvis|thanks|thank you|good morning|good evening)\b)', text))


def wants_detail(text):
    return bool(re.search(r'\b(?:in detail|more detail|detailed|explain fully|step by step)\b', text, re.I))


def trim_answer(text, detailed=False):
    if not isinstance(text, str):
        return ''
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S).strip()
    if '<think>' in text or '<tool_call' in text:
        return ''
    text = re.sub(r'[`*#]', '', text)
    sentences = re.split(r'(?<=[.!?])\s+', ' '.join(text.split()))
    out = ' '.join(sentences[:3 if detailed else 1])
    words = out.split()
    limit = 75 if detailed else 30
    if len(words) > limit:
        out = ' '.join(words[:limit]).rstrip(',;:') + '.'
    return out


def payload_for(text, history=()):
    if not isinstance(text, str) or not 2 <= len(text.strip()) <= 1500 or not text.isprintable():
        raise ValueError("Invalid question")
    detailed = wants_detail(text)
    options = dict(OPTIONS, temperature=.2, top_p=.8, num_predict=160 if detailed else 100)
    return {'model': MODEL, 'messages': [{'role':'system', 'content':PROMPT},
                                       *list(history)[-6:], {'role':'user', 'content':text}],
            'stream':False, 'keep_alive':KEEP_ALIVE, 'options':options}


def answer(text, cancel, history=()):
    result = local_json(payload_for(text, history), 12, cancel=cancel)
    message = result.get('message', {})
    if not result.get('done') or message.get('tool_calls'):
        raise ValueError('Incomplete or invalid general answer')
    reply = trim_answer(message.get('content'), wants_detail(text))
    if not reply:
        raise ValueError('No usable general answer')
    return reply, {key: result.get(key) for key in ('load_duration', 'prompt_eval_duration', 'eval_duration')}
