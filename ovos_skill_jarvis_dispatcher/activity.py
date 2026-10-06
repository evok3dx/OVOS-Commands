"""Bounded in-memory results, never transcripts or user-supplied labels."""
from collections import deque
from datetime import datetime
import json
import threading
import time
import uuid

QUERY_EVENT = 'jarvis.activity.snapshot'
FRAME = 'JARVIS_ACTIVITY_SNAPSHOT='
LIMIT = 32
APP_NAMES = {
    'brave': 'Brave', 'firefox': 'Firefox', 'standard_notes': 'Notes',
    'onlyoffice': 'ONLYOFFICE', 'signal': 'Signal', 'zoom': 'Zoom',
    'terminal': 'Terminal', 'files': 'Files', 'calculator': 'Calculator',
    'settings': 'Settings', 'hermes_desktop': 'Hermes',
    'proton_mail': 'Proton Mail', 'default_mail': 'Mail',
    'proton_calendar': 'Calendar', 'system_calendar': 'Calendar',
    'claude_desktop': 'Claude', 'chatgpt_desktop': 'ChatGPT',
}
VERBS = {'open': 'Opened', 'focus': 'Focused', 'minimize': 'Minimised',
         'maximize': 'Maximised', 'close': 'Closed', 'restore': 'Restored'}
LABELS = {'reading.selection': 'Started reading selected text',
          'reading.page': 'Started reading the page',
          'dictation.start': 'Started dictation', 'dictation.stop': 'Stopped dictation',
          'notes.new': 'Created a new note', 'notes.search': 'Searched Notes'}


def describe(action, integration=None):
    if not isinstance(action, str) or (integration is not None and not isinstance(integration, str)):
        return None
    if action in LABELS:
        return LABELS[action]
    parts = action.split('.') if isinstance(action, str) else []
    if len(parts) == 2 and parts[1] in VERBS:
        if parts[0] == 'window':
            return VERBS[parts[1]] + ' the current window'
        if parts[0] == 'application':
            return VERBS[parts[1]] + ' ' + APP_NAMES.get(integration, 'an application')
    return None


class ActivityLog:
    def __init__(self):
        self._lock = threading.Lock()
        self._rows = deque(maxlen=LIMIT)
        self._session = uuid.uuid4().hex

    def record(self, action, success=True, integration=None):
        text = describe(action, integration)
        if text is None or type(success) is not bool:
            return
        row = {'action': action, 'integration': integration if integration in APP_NAMES else None,
               'success': success, 'time': datetime.now().strftime('%H:%M')}
        with self._lock:
            self._rows.appendleft((time.monotonic(), row))

    def snapshot(self):
        with self._lock:
            deadline = time.monotonic() - 300
            while self._rows and self._rows[-1][0] <= deadline:
                self._rows.pop()
            return {'schema_version': 1, 'session': self._session,
                    'rows': [dict(row) for _, row in self._rows]}

    def clear(self):
        with self._lock:
            self._rows.clear()


def display_rows(value):
    """Validate IPC results and derive every displayed word locally."""
    if not isinstance(value, dict) or value.get('schema_version') != 1:
        raise ValueError('Activity format is unavailable')
    rows = value.get('rows')
    if not isinstance(rows, list) or len(rows) > LIMIT:
        raise ValueError('Activity size is invalid')
    result = []
    for row in rows:
        if not isinstance(row, dict) or type(row.get('success')) is not bool:
            raise ValueError('Activity result is invalid')
        action, integration = row.get('action'), row.get('integration')
        if integration is not None and (not isinstance(integration,str) or integration not in APP_NAMES):
            raise ValueError('Activity application is invalid')
        text = describe(action, integration)
        stamp = row.get('time', '')
        if (text is None or not isinstance(stamp, str) or len(stamp) != 5
                or stamp[2] != ':' or not (stamp[:2] + stamp[3:]).isdigit()
                or int(stamp[:2]) > 23 or int(stamp[3:]) > 59):
            raise ValueError('Activity row is invalid')
        result.append((text if row['success'] else 'Could not complete: ' + text,
                       stamp, row['success']))
    return result


def display_output(output):
    """Read one framed snapshot without treating diagnostic logs as JSON."""
    if not isinstance(output, str) or len(output.encode()) > 65536:
        raise ValueError('Activity response exceeds its limit')
    frames = [line[len(FRAME):] for line in output.splitlines() if line.startswith(FRAME)]
    if len(frames) != 1 or len(frames[0].encode()) > 16384:
        raise ValueError('Activity snapshot is unavailable')
    return display_rows(json.loads(frames[0]))
