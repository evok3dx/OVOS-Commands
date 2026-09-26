"""Tested v4 classifier. Model output is data, never executable code."""
import hashlib
import http.client
import json
import re
import socket
import threading
import time
from pathlib import Path

from . import routing_prompt as source
from . import profile as app_profiles

MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
KEEP_ALIVE = -1
OPTIONS = {'temperature': 0, 'seed': 42, 'num_ctx': 4096,
           'num_predict': 64, 'num_batch': 256}


def load_profile():
    root = Path.home() / '.config/jarvis'
    path = root / 'capabilities.json'
    if not path.is_file():
        path = root / 'profile.json'
    if path.stat().st_size > 65536:
        raise ValueError('Oversized application profile')
    raw = json.loads(path.read_text())
    if raw.get('mode') == 'all-detected':
        raw['applications'] = dict(raw.get('applications', {}))
        raw['applications'].update({key:key for key in app_profiles.discovered_applications()})
    return source.resolve_profile(raw)


def normalise(text):
    return ' '.join(re.findall(r'\w+', text.casefold()))


def file_search_request(utterance):
    """Extract a bounded filename query from the original spoken request."""
    if not isinstance(utterance, str) or not 2 <= len(utterance.strip()) <= 300 or not utterance.isprintable():
        return None
    text = utterance.strip()
    text = re.sub(r'^(?:(?:hey )?jarvis[, ]+)?(?:please\s+|can you\s+|could you\s+|would you\s+|will you\s+)*', '', text, flags=re.I)
    match = re.match(r'^(?:find|locate|search(?:ing)?|look(?:ing)?)\b\s*(.*)$', text, re.I)
    if not match:
        return None
    tail = match.group(1).strip()
    if (re.search(r'\b(?:and|then)\s+(?:open|delete|read|send|move|copy|rename|share|edit)\b', tail, re.I)
            or re.search(r'\b(?:when|after|if)\b', tail, re.I)
            or re.search(r'^\s*at\b', tail, re.I)):
        return None
    # Keep search engine, mail and notes requests with their own integrations.
    if re.search(r'\b(?:youtube|web|internet|online|brave|firefox|mail|email|notes)\b', tail, re.I):
        return None
    documents_only = bool(re.search(r'\b(?:(?:in|inside|through)\s+)?my\s+documents\b|\b(?:in|inside|through)\s+documents\b', tail, re.I))
    tail = re.sub(r'\b(?:in|inside|through)\s+(?:my\s+)?documents\b', ' ', tail, flags=re.I)
    # "looking my documents for Alex" is a common transcription variant.
    tail = re.sub(r'^(?:(?:in|through|inside|of|for)\s+)?(?:my\s+)?(?:files?|documents?|folders?)\s+for\s+', '', tail, flags=re.I)
    tail = re.sub(r'^\s*(?:(?:my|the)\s+)?(?:files?|documents?|folders?)\s+for\s+', '', tail, flags=re.I)
    tail = re.sub(r'^\s*(?:for|about|named|called)\s+', '', tail, flags=re.I)
    tail = re.sub(r'^\s*(?:(?:my|the)\s+)?(?:files?|documents?|folders?)\s+(?:named|called|about)\s+', '', tail, flags=re.I)
    tail = re.sub(r'^\s*(?:the|a|an)\s+', '', tail, flags=re.I)
    tail = re.sub(r'\s+(?:please|for me)\s*$', '', tail, flags=re.I)
    query = tail.strip(' \t.,!?')
    if (not query or len(query) > 200 or not re.search(r'\w', query)
            or query.casefold() in {'file', 'files', 'document', 'documents', 'my files', 'this file', 'that file'}):
        return None
    return {'query': query, 'documents_only': documents_only}


def named_targets(text, profile):
    """Longest overlapping name wins: Proton Mail must not also match Mail.

    Disabled known integrations participate so their names cannot be silently
    resolved to an enabled application. Ambiguous equal aliases fail closed.
    """
    text = normalise(text)
    matches = []
    apps = profile['applications']
    # Reuse the chooser's registry and discovery, including disabled names.
    # Retain the frozen benchmark definitions only for canonical category hints.
    definitions = {**app_profiles.APPLICATION_INTEGRATIONS,
                   **app_profiles.discovered_applications()}
    for value in apps.values():
        integration = value['integration']
        previous = definitions.get(integration, {})
        definitions[integration] = {
            'display_name': value['display_name'],
            'aliases': list(dict.fromkeys([*previous.get('aliases', []), *value['aliases']]))}
    for integration, definition in definitions.items():
        targets = {key for key, value in apps.items()
                   if value['integration'] == integration}
        # Keep explicit Proton Mail distinct even in legacy duplicate mappings.
        category = source._APPLICATIONS.get(integration, {}).get('detection', {}).get('category', integration)
        if category in targets:
            targets = {category}
        targets = targets or {'!disabled:' + integration}
        aliases = [definition['display_name'], *definition['aliases']]
        personal_name = profile.get('spoken_names', {}).get(integration)
        if personal_name:
            aliases.append(personal_name)
        for alias in dict.fromkeys(normalise(a) for a in aliases):
            if not alias:
                continue
            for match in re.finditer(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text):
                matches.append((match.start(), match.end(), targets))
    maximal = [m for m in matches if not any(
        n[0] <= m[0] and n[1] >= m[1] and n[1]-n[0] > m[1]-m[0]
        for n in matches)]
    return set().union(*(m[2] for m in maximal)) if maximal else set()


def candidates_for(utterance, catalogue, profile):
    if not isinstance(utterance, str) or not 2 <= len(utterance.strip()) <= 300 or not utterance.isprintable():
        raise ValueError('Invalid utterance')
    targets = named_targets(utterance, profile)
    file_candidate = {'files.search': catalogue['files.search']} if (
        'files.search' in catalogue and file_search_request(utterance)) else {}
    if len(targets) > 1 or any(t.startswith('!disabled:') for t in targets):
        return {}
    if targets:
        target = next(iter(targets))
        ids = {f'application.{op}.{target}' for op in source.APP_ROUTER_OPERATIONS}
        ids.update({'brave': {'browser.search_brave'},
                    'firefox': {'browser.search_firefox'},
                    'notes': {'notes.search'},
                    'proton_mail': {'mail.search'}}.get(target, set()))
        if target == 'mail' and profile['applications'][target]['integration'] == 'proton_mail':
            ids.add('mail.search')
        return {**{a: v for a, v in catalogue.items() if a in ids}, **file_candidate}
    text = normalise(utterance)
    speed_fast = bool(re.search(
        r'\b(?:2\s*x|two\s*x|twice|double(?:\s+the)?\s+speed|'
        r'two\s+times(?:\s+(?:the\s+)?speed)?)\b',
        utterance, re.I,
    ))
    reading_target = ('page' if re.search(
        r'\b(?:page|webpage|window|screen|article)\b', text,
    ) else 'selection')
    reading_action = 'reading.' + reading_target + ('_fast' if speed_fast else '')
    current_window = bool(re.search(
        r'\b(?:this|current|active|focused) (?:(?:maximised|maximized|normal|resizable) )?window\b'
        r'|\bwhat i am looking at\b|\bthe window i am (?:using|looking at)\b', text))
    # A known named target is required for every application-specific action.
    # Generic window operations additionally need an explicit current-window
    # reference, preventing "Make Calculator's window bigger" being applied
    # to an unrelated focused window.
    return {a: v for a, v in catalogue.items()
            if not a.startswith('application.')
            and (not a.startswith(('reading.selection', 'reading.page'))
                 or a == reading_action)
            and (a != 'files.search' or file_candidate)
            and a not in {'browser.search_brave', 'browser.search_firefox', 'notes.search', 'mail.search'}
            and (not a.startswith('window.') or current_window)
            and (a != 'browser.search_youtube' or re.search(r'\byoutube\b', text))}


def response_actions(allowed):
    """Short transport IDs resolve only within this request's approved actions."""
    targets = {a.split('.', 2)[2] for a in allowed if a.startswith('application.')}
    compact = len(targets) == 1
    mapping = {}
    for action in sorted(allowed):
        wire = '.'.join(action.split('.')[:2]) if compact and action.startswith('application.') else action
        if wire in mapping:
            raise ValueError('Ambiguous response action')
        mapping[wire] = action
    return mapping


def payload_for(utterance, catalogue, profile, model=MODEL):
    allowed = candidates_for(utterance, catalogue, profile)
    # Use the same v3 decision rules; reduce only the action and alias context.
    targets = named_targets(utterance, profile)
    reduced = dict(profile, applications={k: v for k, v in profile['applications'].items()
                                         if k in targets})
    template = source.payload_for(utterance, allowed, reduced)
    mapping = response_actions(allowed)
    # Only trusted system text/schema change. Preserve the user's words exactly.
    system = template['messages'][0]['content']
    for wire, action in sorted(mapping.items(), key=lambda item: -len(item[1])):
        system = system.replace(action, wire)
    template['messages'][0]['content'] = system
    template['response_format']['json_schema']['schema']['properties']['action']['enum'] = ['none', *mapping]
    payload = {'model': model, 'messages': template['messages'], 'stream': False,
               'format': template['response_format']['json_schema']['schema'],
               'keep_alive': KEEP_ALIVE, 'options': OPTIONS.copy()}
    return payload, allowed


class RequestCancelled(Exception):
    """The user started a new request or stopped the current one."""


def local_json(payload, timeout, *, port=11434, cancel=None):
    """Loopback only, no proxies/redirects/retries, bounded body and wall time."""
    if type(timeout) not in (float, int) or not 0 < timeout <= 120:
        raise ValueError('Invalid timeout')
    deadline = time.monotonic() + timeout
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    watchdog = None
    cancellation_thread = None
    finished = threading.Event()
    try:
        if cancel is not None and cancel.is_set():
            raise RequestCancelled()
        connection.connect()
        transport = connection.sock

        def expire():
            try:
                transport.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        watchdog = threading.Timer(max(.001, deadline - time.monotonic()), expire)
        watchdog.daemon = True
        watchdog.start()
        if cancel is not None:
            def interrupt():
                while not finished.wait(.05):
                    if cancel.is_set():
                        expire()
                        return
            cancellation_thread = threading.Thread(target=interrupt, daemon=True)
            cancellation_thread.start()
        connection.request('POST', '/api/chat', body=json.dumps(payload).encode(),
                           headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError('Ollama HTTP status ' + str(response.status))
        body = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Model deadline exceeded')
            if connection.sock:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(4096, 65537 - len(body)))
            body.extend(chunk)
            if len(body) > 65536:
                raise ValueError('Oversized Ollama response')
            if not chunk:
                break
        if time.monotonic() > deadline:
            raise TimeoutError('Model deadline exceeded')
        if cancel is not None and cancel.is_set():
            raise RequestCancelled()
        result = json.loads(body, object_pairs_hook=source._unique_object)
        if not isinstance(result, dict):
            raise ValueError('Invalid Ollama response')
        return result
    except (OSError, http.client.HTTPException) as error:
        if cancel is not None and cancel.is_set():
            raise RequestCancelled() from error
        if time.monotonic() >= deadline:
            raise TimeoutError("Model deadline exceeded") from error
        raise
    finally:
        finished.set()
        if watchdog:
            watchdog.cancel()
        connection.close()


def classify(utterance, catalogue, profile, *, model=MODEL, timeout=8, cancel=None):
    started = time.monotonic()
    payload, allowed = payload_for(utterance, catalogue, profile, model)
    info = {'candidate_count': len(allowed), 'model_action': 'none',
            'payload_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            'error': None, 'timing_ns': {}, 'actual': 'none', 'policy_rejected': False}
    if not allowed:
        info.update(seconds=round(time.monotonic() - started, 4), skipped_model=True)
        return info
    result = local_json(payload, timeout, cancel=cancel)
    message = result.get('message')
    if result.get('done') is not True or result.get('done_reason') != 'stop' or not isinstance(message, dict) or message.get('tool_calls'):
        raise ValueError('Incomplete completion or unexpected tool call')
    # Resolve only through the mapping built from this request's allowed set.
    # A model can neither choose another target nor provide an executable command.
    mapping = response_actions(allowed)
    wire = source.parse_action(message.get('content'), mapping)
    action = 'none' if wire == 'none' else mapping[wire]
    rejected = action != 'none' and action not in allowed
    info.update(model_action=action, actual='none' if rejected else action,
                policy_rejected=rejected, skipped_model=False,
                seconds=round(time.monotonic() - started, 4),
                timing_ns={key: result.get(key) for key in (
                    'load_duration', 'prompt_eval_duration', 'prompt_eval_count',
                    'eval_duration', 'eval_count', 'total_duration')})
    return info
