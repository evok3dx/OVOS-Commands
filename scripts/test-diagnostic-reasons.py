#!/usr/bin/env python3
"""Useful diagnostic labels without private content or misleading silence."""
import copy
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import patch

if os.getuid() == 0:
    raise RuntimeError('Run diagnostic regressions as the ordinary user')
sys.path.insert(0, str(Path(__file__).resolve().parent))
import privacy_logging as privacy
import diagnostic_reader as reader
import isolation_services

SECRET = 'PRIVATE-DICTATION-QUERY-CLIPBOARD-SENTINEL'


def record(module, function, message, args=(), level=logging.INFO):
    item = logging.LogRecord(SECRET, level, '/private/' + SECRET, 42,
                             message, args, (RuntimeError, RuntimeError(SECRET), None), function)
    item.module = module
    # Any accidental format call is a regression, including harmless templates.
    item.getMessage = lambda: (_ for _ in ()).throw(AssertionError('Message formatted'))
    return item


with tempfile.TemporaryDirectory() as temporary:
    home = Path(temporary)
    clock = [20.0]
    with patch.object(privacy.time, 'monotonic', side_effect=lambda: clock[0]):
        privacy.set_mode(True, home)
        core, media, weather = (privacy.Capture(role, home) for role in ('core', 'media', 'weather'))
        cases = [
            (media, '__init__', '_search_and_open', 'Opened first YouTube result in %s: %s', (SECRET, SECRET), logging.INFO, 'result-open'),
            (core, '__init__', '_search_and_open', 'Media request failed: %s', (RuntimeError(SECRET),), logging.WARNING, 'media-request-failed'),
            (media, '__init__', '_search_and_open', 'YouTube result search timed out', (), logging.WARNING, 'search-timeout'),
            (media, '__init__', '_control', 'Media action ignored; no compatible player: %s', (SECRET,), logging.INFO, 'media-no-player'),
            (core, 'desktop', '_run_desktop_app_action', SECRET, (), logging.ERROR, 'app-focus-failed'),
            (core, 'helpers', '_read_visible_text', 'Reading request failed: mode=%s code=%s', ('selection', 20), logging.WARNING, 'reading-no-selection'),
            (core, 'helpers', '_read_visible_text', 'Reading request failed: mode=%s code=%s', (SECRET, 22), logging.WARNING, 'reading-start-failed'),
            (core, 'helpers', '_read_visible_text', 'Reading request failed: mode=%s code=%s', (SECRET, SECRET), logging.WARNING, 'reading-failed'),
            (core, 'routing_pipeline', 'match', 'Qwen router unavailable (%s)', (SECRET,), logging.WARNING, 'qwen-router-unavailable'),
            (weather, 'weather_boundary', 'request', 'Weather provider %s operation: %.2f seconds', ('search', SECRET), logging.INFO, 'weather-search'),
            (weather, 'weather_boundary', 'call', 'Weather %s stage: %.2f seconds', ('speech submission', SECRET), logging.INFO, 'weather-speech'),
        ]
        for capture, module, function, message, args, level, expected in cases:
            clock[0] += 1
            capture.handle(record(module, function, message, args, level))
            value = capture.snapshot()
            assert value['rows'][0]['reason'] == expected, value
            assert value['rows'][0]['elapsed'] == clock[0] - 20
            assert SECRET not in json.dumps(value) + '\n'.join(privacy.display(value))
        before = len(media.rows)
        media.handle(record('__init__', '_search_and_open', SECRET, (SECRET,)))
        media.handle(record('weather_boundary', 'request', 'Weather provider %s operation: %.2f seconds', (SECRET, 1)))
        assert len(media.rows) == before, 'Unreviewed informational content was retained'
        # Unknown warnings still retain a location/severity, with no free text.
        core.handle(record('unknown', 'unknown', SECRET, (SECRET,), logging.ERROR))
        assert 'reason' not in core.snapshot()['rows'][0]
        assert SECRET not in json.dumps(core.snapshot())

        valid = media.snapshot()
        for field, value in [('reason', SECRET), ('elapsed', float('nan')),
                             ('elapsed', float('inf')), ('elapsed', True),
                             ('elapsed', -1), ('elapsed', 301), ('message', SECRET)]:
            forged = copy.deepcopy(valid)
            forged['rows'][0][field] = value
            try:
                privacy.display(forged)
            except ValueError:
                pass
            else:
                raise AssertionError('Unreviewed diagnostic field accepted')
        privacy.set_mode(True, home)
        assert privacy.mode(home)['start'] == 20, 'Diagnostics extended by another click'
        clock[0] = 320
        assert core.snapshot()['rows'] == media.snapshot()['rows'] == weather.snapshot()['rows'] == []


calls = []
closed = []
responses = {
    'core': types.SimpleNamespace(data={'schema_version': 1, 'component': 'core', 'rows': []}),
    'audio': types.SimpleNamespace(data={'schema_version': 1, 'component': 'audio', 'rows': [
        {'component': 'audio', 'level': 'ERROR', 'event': 'error', 'source': 'runtime', 'line': 2, 'message': SECRET}]}),
    'weather': types.SimpleNamespace(data={'schema_version': 1, 'component': 'core', 'rows': []}),
}


class Bus:
    connected_event = types.SimpleNamespace(wait=lambda _: True)

    def __init__(self, **kwargs):
        assert kwargs == dict(host='127.0.0.1', port=8181, route='/core', ssl=False)

    def run_in_thread(self):
        pass

    def wait_for_response(self, message, topic, timeout):
        assert timeout == 2
        role = topic.split('.')[2]
        calls.append(role)
        return responses.get(role)

    def close(self):
        closed.append(True)


with patch.dict(sys.modules, {'ovos_bus_client': types.SimpleNamespace(MessageBusClient=Bus, Message=lambda _: None)}):
    for isolated in (False, True):
        calls.clear()
        with patch.object(reader, 'mode', return_value={'enabled': True}), patch.object(isolation_services, 'active', return_value=isolated):
            result = reader.read()
        assert SECRET not in result
        assert 'core: diagnostic collector responding.' in result
        assert 'listener: no diagnostic response' in result
        assert 'audio: diagnostic response unavailable or invalid.' in result
        assert ('weather' in calls) is isolated and ('media' in calls) is isolated
        if isolated:
            assert 'weather: diagnostic response unavailable or invalid.' in result
    with patch.object(reader, 'mode', side_effect=[{'enabled': True}, {'enabled': False}]), patch.object(isolation_services, 'active', return_value=True):
        assert reader.read() == 'Diagnostics finished. No logs are being kept.'
    calls.clear()
    with patch.object(reader, 'mode', return_value={'enabled': False}):
        assert reader.read().startswith('No logs.')
    assert not calls and len(closed) == 3

print('PASS: fixed reasons, private-content exclusion, strict wire fields, elapsed clock, unchanged expiry, collector availability and ordinary/isolated roles')
