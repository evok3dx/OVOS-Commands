"""No raw application logs; five-minute, content-free diagnostic capture.

Readiness is current process state, not historical logging. Diagnostic rows
stay in process memory and expire independently of the Control Centre.
"""
from collections import deque
import atexit
import json
import logging
import math
import os
from pathlib import Path
import stat
import tempfile
import threading
import time

WINDOW = 300
LIMIT = 256
ROLES = ('core', 'listener', 'audio', 'weather', 'media', 'bus')
EVENTS = ('ready', 'technical', 'warning', 'error')
LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
SOURCES = ('runtime', 'desktop', 'dictation', 'browser', 'conversation',
           'routing_model', 'routing_runtime', 'weather_boundary', 'pipeline',
           'media', 'voice_loop', 'service', 'client', '__init__', '__main__',
           'helpers', 'routing_pipeline')
# Codes and labels are reviewed constants. Never display a log message, even
# when its template looks harmless: arguments can contain speech or secrets.
REASONS = {
    'component-ready': 'Component ready',
    'media-ready': 'Music helper ready',
    'search-wait': 'Waiting for the shared search gap',
    'search-start': 'Music lookup started',
    'search-finish': 'Music lookup finished',
    'result-open': 'Music result opened',
    'provider-refused': 'Music provider refused the request',
    'search-timeout': 'Music lookup timed out',
    'media-request-failed': 'Music lookup or launch failed',
    'media-invalid-action': 'Unrecognised media control rejected',
    'media-control-sent': 'Media control sent',
    'media-no-player': 'No compatible playback session',
    'media-tool-missing': 'Media control tool unavailable',
    'media-control-failed': 'Media control failed',
    'app-focus-failed': 'Application launch or focus failed',
    'window-control-failed': 'Window control failed',
    'reading-failed': 'Reading request failed',
    'reading-no-selection': 'No selected text found',
    'reading-start-failed': 'Speech Note reading could not start',
    'reading-starting': 'Speech Note reading is still starting',
    'browser-failed': 'Browser action failed',
    'qwen-router-unavailable': 'Qwen command routing unavailable',
    'qwen-answer-unavailable': 'Qwen answer unavailable',
    'qwen-dispatch-failed': 'Qwen action dispatch failed',
    'empty-transcription': 'No transcription returned: silence or speech recognition failure',
    'weather-location': 'Weather location stage finished',
    'weather-forecast': 'Weather forecast stage finished',
    'weather-display': 'Weather display stage finished',
    'weather-speech': 'Weather speech submission stage finished',
    'weather-search': 'Weather location search finished',
    'weather-reverse': 'Weather reverse lookup finished',
    'weather-details': 'Weather location details lookup finished',
    'weather-provider-forecast': 'Weather provider forecast request finished',
}
MEDIA_TEMPLATES = {
    ('initialize', 'Jarvis Media ready (%s)'): 'media-ready',
    ('_wait_search_slot', 'Waiting for the shared search gap'): 'search-wait',
    ('_search_and_open', 'Reserved one bounded YouTube title lookup'): 'search-start',
    ('_search_and_open', 'YouTube lookup completed in %.2f seconds'): 'search-finish',
    ('_search_and_open', 'Opened first YouTube result in %s: %s'): 'result-open',
    ('_search_and_open', 'YouTube refused the search request'): 'provider-refused',
    ('_search_and_open', 'YouTube result search timed out'): 'search-timeout',
    ('_search_and_open', 'Media request failed: %s'): 'media-request-failed',
    ('_handle_control', 'Rejected unknown Media action'): 'media-invalid-action',
    ('_control', 'Media action sent%s: %s'): 'media-control-sent',
    ('_control', 'Media action ignored; no compatible player: %s'): 'media-no-player',
    ('_control', 'playerctl is unavailable'): 'media-tool-missing',
    ('_control', 'Media action failed: %s'): 'media-control-failed',
}


def reason(record, role, is_ready=False):
    """Classify reviewed sites without formatting or retaining private data."""
    if is_ready:
        return 'component-ready'
    module, function, message = record.module, record.funcName, record.msg
    if any(type(value) is not str for value in (module, function, message)):
        return None
    if role in ('core', 'media') and module == '__init__':
        return MEDIA_TEMPLATES.get((function, message))
    if role == 'listener' and (module, function, message) == (
            'service', '_stt_text', 'Empty transcription, either recorded silence or STT failed!'):
        return 'empty-transcription'
    if role in ('core', 'weather') and module == 'weather_boundary':
        if function == 'intent_data' and message == 'Weather intent/location stage: %.2f seconds':
            return 'weather-location'
        # Only a fixed enum is read. Location, query and duration arguments
        # are never copied; elapsed time comes from our own capture clock.
        if type(record.args) is tuple and record.args and type(record.args[0]) is str:
            name = record.args[0]
            if function == 'call' and message == 'Weather %s stage: %.2f seconds':
                return {'forecast': 'weather-forecast', 'display': 'weather-display',
                        'speech submission': 'weather-speech'}.get(name)
            if function == 'request' and message == 'Weather provider %s operation: %.2f seconds':
                return {'search': 'weather-search', 'reverse': 'weather-reverse',
                        'details': 'weather-details', 'forecast': 'weather-provider-forecast'}.get(name)
    if role != 'core' or record.levelno < logging.WARNING:
        return None
    if module == 'desktop':
        return {'_run_desktop_app_action': 'app-focus-failed',
                '_focused_window_action': 'window-control-failed'}.get(function)
    if module == 'helpers' and function == '_read_visible_text':
        if message == 'Reading request failed: mode=%s code=%s' and type(record.args) is tuple and len(record.args) == 2:
            mode_value, code = record.args
            if type(code) is int:
                if type(mode_value) is str and mode_value == 'selection' and code == 20:
                    return 'reading-no-selection'
                if code in (22, 23):
                    return {22: 'reading-start-failed', 23: 'reading-starting'}[code]
        return 'reading-failed'
    if module == 'browser' and function in (
            '_run_browser_action', '_prompt_browser_search', '_submit_prompted_browser_search',
            '_prompt_youtube_search', '_open_youtube_shorts', '_open_fixed_website'):
        return 'browser-failed'
    return {('routing_pipeline', 'Qwen router unavailable (%s)'): 'qwen-router-unavailable',
            ('routing_pipeline', 'Qwen answer pipeline unavailable (%s)'): 'qwen-answer-unavailable',
            ('routing_runtime', 'Qwen dispatch failed (%s)'): 'qwen-dispatch-failed',
            ('routing_runtime', 'Qwen answer unavailable (%s)'): 'qwen-answer-unavailable'}.get((module, message))
_capture = None


def directory(home=None):
    return Path(home or Path.home()) / '.local/state/jarvis/privacy'


def checked(path, directory_only=False):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Privacy storage must not use symbolic links')
    if path.exists():
        info = path.stat()
        if (info.st_uid != os.getuid() or info.st_mode & 0o077
                or (not stat.S_ISDIR(info.st_mode) if directory_only else not stat.S_ISREG(info.st_mode))):
            raise ValueError('Privacy storage ownership or permissions need review')
        if not directory_only and info.st_size > 65536:
            raise ValueError('Privacy state exceeds its limit')
    return path


def write(path, value):
    root = checked(path.parent, True)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    checked(path)
    fd, name = tempfile.mkstemp(prefix='.state-', dir=root)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def mode(home=None, now=None):
    """Missing, invalid, expired or previous-boot control always means off."""
    try:
        checked(directory(home), True)
        path = checked(directory(home) / 'capture.json')
        data = json.loads(path.read_text())
        clock = time.monotonic() if now is None else now
        start, end = data.get('start'), data.get('end')
        valid = (isinstance(data, dict) and data.get('schema_version') == 1
                 and data.get('boot') == boot()
                 and type(start) in (int, float) and type(end) in (int, float)
                 and math.isfinite(start) and math.isfinite(end)
                 and abs((end - start) - WINDOW) <= 1e-6 and start <= clock < end)
        return {'enabled': bool(valid), 'remaining': math.ceil(end - clock) if valid else 0,
                'start': start if valid else None}
    except (OSError, ValueError, TypeError, AttributeError):
        return {'enabled': False, 'remaining': 0, 'start': None}


def set_mode(enabled, home=None):
    if type(enabled) is not bool or os.getuid() == 0:
        raise ValueError('Choose a logging mode as the desktop user')
    path = directory(home) / 'capture.json'
    if enabled:
        if mode(home)['enabled']:
            return mode(home)  # Repeated clicks never extend an active capture.
        start = time.monotonic()
        write(path, {'schema_version': 1, 'boot': boot(), 'start': start, 'end': start + WINDOW})
    else:
        write(path, {'schema_version': 1})
    return mode(home)


def readiness(role, invocation, home=None):
    """Return None for a legacy worker, False for a managed worker still loading."""
    if role not in ROLES or not invocation:
        return None
    try:
        checked(directory(home), True)
        data = json.loads(checked(directory(home) / (role + '-ready.json')).read_text())
        if (not isinstance(data, dict) or data.get('schema_version') != 1
                or data.get('boot') != boot() or data.get('invocation') != invocation):
            return None
        pid = data.get('pid')
        if type(pid) is not int or pid <= 0 or type(data.get('ready')) is not bool:
            return False
        # Invocation identity and process existence reject stale state after
        # restart/stop; the GUI also requires the actual unit to be active.
        os.kill(pid, 0)
        return data['ready']
    except (OSError, ValueError, TypeError):
        return None


class Capture:
    def __init__(self, role, home=None):
        if role not in ROLES:
            raise ValueError('Unknown managed component')
        self.role, self.home = role, home
        self.rows = deque(maxlen=LIMIT)
        self.lock = threading.RLock()
        self.stopped = threading.Event()
        self.session = None
        self.ready = False
        self.invocation = os.environ.get('INVOCATION_ID', '')
        self.publish_ready()

    def publish_ready(self):
        write(directory(self.home) / (self.role + '-ready.json'),
              {'schema_version': 1, 'boot': boot(), 'invocation': self.invocation,
               'pid': os.getpid(), 'ready': self.ready})

    def prune(self, now=None):
        clock = time.monotonic() if now is None else now
        current = mode(self.home, clock)
        with self.lock:
            if not current['enabled'] or current['start'] != self.session:
                self.rows.clear()
                self.session = current['start']
            while self.rows and self.rows[-1]['tick'] <= clock - WINDOW:
                self.rows.pop()
        return current

    def handle(self, record):
        # Never call getMessage(), format a traceback or retain record.args.
        # Readiness accepts only the exact reviewed message for this process.
        ready_message = {'core': 'Jarvis configuration ready',
                         'listener': 'DinkumVoiceService is ready.'}.get(self.role)
        is_ready = ready_message is not None and type(record.msg) is str and record.msg == ready_message
        if is_ready and not self.ready:
            self.ready = True
            self.publish_ready()
        current = self.prune()
        if not current['enabled']:
            return
        level = logging.getLevelName(record.levelno)
        if level not in LEVELS:
            return
        code = reason(record, self.role, is_ready)
        if code is None and record.levelno < logging.WARNING:
            return  # Unknown informational traffic is noise, not useful evidence.
        event = 'ready' if is_ready else 'error' if record.levelno >= 40 else 'warning' if record.levelno >= 30 else 'technical'
        line = record.lineno if type(record.lineno) is int and 0 <= record.lineno < 1000000 else 0
        source = record.module if record.module in SOURCES else 'runtime'
        with self.lock:
            clock = time.monotonic()
            row = {'tick': clock, 'component': self.role,
                   'level': level, 'event': event, 'source': source, 'line': line}
            if code is not None:
                row.update(reason=code, elapsed=round(max(0, min(WINDOW, clock - current['start'])), 1))
            self.rows.appendleft(row)

    def snapshot(self):
        current = self.prune()
        with self.lock:
            return {'schema_version': 1, 'component': self.role,
                    'remaining': current['remaining'],
                    'rows': [{k: v for k, v in row.items() if k != 'tick'} for row in self.rows]}

    def sweep(self):
        while not self.stopped.wait(1):
            self.prune()


def suppress_output():
    """Suppress direct prints, native warnings and inherited player output."""
    fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(fd, 1)
        os.dup2(fd, 2)
    finally:
        os.close(fd)


def quiet_reader():
    """Keep one result descriptor; discard all third-party reader output/logs."""
    if os.getuid() == 0:
        raise RuntimeError('Read Jarvis state as the desktop user')
    output = os.dup(1)
    os.set_inheritable(output, False)
    suppress_output()
    logging.Logger.callHandlers = lambda _logger, _record: None
    logging.FileHandler._open = lambda _handler: open(os.devnull, 'a', encoding='utf-8')
    return output


def bootstrap(role):
    global _capture
    if os.getuid() == 0:
        raise RuntimeError('Start Jarvis as the desktop user')
    if _capture is not None:
        if _capture.role != role:
            raise RuntimeError('Managed worker identity changed')
        return _capture
    suppress_output()
    _capture = Capture(role)
    logging.Logger.callHandlers = lambda _logger, record: _capture.handle(record)
    # Upstream logger configuration may construct a file handler even when
    # records are suppressed. Do not create or reopen its historical log file.
    logging.FileHandler._open = lambda _handler: open(os.devnull, 'a', encoding='utf-8')
    install_process_status()
    atexit.register(_capture.stopped.set)
    threading.Thread(target=_capture.sweep, name='Jarvis diagnostic expiry', daemon=True).start()
    return _capture


def mark_ready(role, ready=True):
    if _capture is not None and _capture.role == role and type(ready) is bool:
        _capture.ready = ready
        _capture.publish_ready()


def install_process_status():
    """Observe actual listener state, independent of configured log levels."""
    from functools import wraps
    from ovos_utils.process_utils import ProcessStatus
    if getattr(ProcessStatus, '_jarvis_privacy_ready', False):
        return
    names = {'core': 'skills', 'listener': 'voice', 'audio': 'audio'}
    for method, ready in (('set_ready', True), ('set_stopping', False), ('set_error', False)):
        original = getattr(ProcessStatus, method)
        def wrap(function, value):
            @wraps(function)
            def changed(status, *args, **kwargs):
                result = function(status, *args, **kwargs)
                capture = _capture
                if capture is not None and getattr(status, 'name', None) == names.get(capture.role):
                    # Core readiness remains the actual dispatcher load point.
                    if capture.role != 'core' or not value:
                        mark_ready(capture.role, value)
                return result
            return changed
        setattr(ProcessStatus, method, wrap(original, ready))
    ProcessStatus._jarvis_privacy_ready = True


def attach(bus):
    if _capture is None:
        raise RuntimeError('Install privacy before starting the bus')
    capture = _capture
    topic = 'jarvis.diagnostics.' + capture.role
    def respond(message):
        bus.emit(message.response(capture.snapshot()))
    bus.on(topic, respond)


def display(value):
    """Untrusted bus data cannot supply a free-text diagnostic label."""
    if not isinstance(value, dict) or value.get('schema_version') != 1 or value.get('component') not in ROLES:
        raise ValueError('Diagnostic format is invalid')
    rows = value.get('rows')
    if not isinstance(rows, list) or len(rows) > LIMIT:
        raise ValueError('Diagnostic size is invalid')
    result = []
    for row in rows:
        fields = {'component', 'level', 'event', 'source', 'line'}
        if (not isinstance(row, dict) or set(row) not in (fields, fields | {'reason', 'elapsed'})
                or row['component'] != value['component'] or row['level'] not in LEVELS
                or row['event'] not in EVENTS or row['source'] not in SOURCES or type(row['line']) is not int
                or not 0 <= row['line'] < 1000000):
            raise ValueError('Diagnostic row is invalid')
        label = row['event']
        elapsed = ''
        if 'reason' in row:
            if (type(row['reason']) is not str or row['reason'] not in REASONS
                    or type(row['elapsed']) not in (int, float) or not math.isfinite(row['elapsed'])
                    or not 0 <= row['elapsed'] <= WINDOW):
                raise ValueError('Diagnostic reason is invalid')
            label = REASONS[row['reason']]
            elapsed = f"+{row['elapsed']:.1f}s · "
        result.append(f"{elapsed}{row['component']}: {row['level'].lower()} · {label} · {row['source']}:{row['line']}")
    return result
