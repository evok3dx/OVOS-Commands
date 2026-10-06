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
           'media', 'voice_loop', 'service', 'client', '__init__', '__main__')
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
        event = 'ready' if is_ready else 'error' if record.levelno >= 40 else 'warning' if record.levelno >= 30 else 'technical'
        line = record.lineno if type(record.lineno) is int and 0 <= record.lineno < 1000000 else 0
        source = record.module if record.module in SOURCES else 'runtime'
        with self.lock:
            self.rows.appendleft({'tick': time.monotonic(), 'component': self.role,
                                  'level': level, 'event': event, 'source': source, 'line': line})

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
        if (not isinstance(row, dict) or set(row) != {'component', 'level', 'event', 'source', 'line'}
                or row['component'] != value['component'] or row['level'] not in LEVELS
                or row['event'] not in EVENTS or row['source'] not in SOURCES or type(row['line']) is not int
                or not 0 <= row['line'] < 1000000):
            raise ValueError('Diagnostic row is invalid')
        result.append(f"{row['component']}: {row['level'].lower()} · {row['event']} · {row['source']}:{row['line']}")
    return result
