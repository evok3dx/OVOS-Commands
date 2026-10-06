#!/usr/bin/env python3
"""Real helper/supervisor processes with an ownership-aware desktop fixture.

No live clipboard, display, Speech Note, services or network are accessed.
The fixture models selection ownership; it is not a live X11 acceptance test.
"""

import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import time


if os.getuid() == 0:
    raise SystemExit("Run clipboard regressions as the normal desktop user, without sudo.")

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "system_helpers/jarvis-read-visible-text"
SUPERVISOR = ROOT / "system_helpers/jarvis-reading-clipboard"

# Exercise the production atomic check/clear with a content-free Xlib peer.
scope = runpy.run_path(str(SUPERVISOR), run_name="clipboard_test")
for owner, pid, clears in ((123, 50, True), (321, 50, False), (123, 51, False)):
    events = []

    class API:
        def XGrabServer(self, display): events.append("grab")
        def XGetSelectionOwner(self, display, atom):
            events.append("owner")
            return owner
        def XSetSelectionOwner(self, display, atom, window, timestamp):
            assert window == timestamp == 0
            events.append("clear")
        def XSync(self, display, discard): events.append("sync")
        def XUngrabServer(self, display): events.append("ungrab")

    connection = scope["X11"].__new__(scope["X11"])
    connection.x, connection.display, connection.atom = API(), 1, 2
    connection.pid = lambda window: pid
    connection.clear_if_owner(123, 50)
    assert ("clear" in events) is clears
    assert events[0] == "grab" and events[-2:] == ["ungrab", "sync"]
    if clears:
        assert events.index("owner") < events.index("clear") < events.index("ungrab")
print("PASS: atomic clear checks the owner window and child process")

# Use real supervisor and shell processes. Substitute only desktop
# peers, so SIGKILL, expiry, child lifetimes and lock inheritance are exercised.
PEER = r'''
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import time

root = Path(os.environ['READING_FIXTURE'])
name = Path(sys.argv[0]).name
(root / 'pids' / str(os.getpid())).write_text(
    Path('/proc/self/stat').read_text().split(') ', 1)[1].split()[19])

def alive(pid):
    try:
        os.kill(pid, 0)
        return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[0] != 'Z'
    except (ProcessLookupError, FileNotFoundError):
        return False

def selection(value=None, owner=None, release=None):
    with (root / 'selection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / 'selection.json'
        current = json.loads(path.read_text()) if path.exists() else {'owner': None, 'text': ''}
        if isinstance(current['owner'], int) and not alive(current['owner']):
            # Cinnamon retains the data when a selection owner disappears.
            current['owner'] = 'manager'
        if release is not None and current['owner'] == release:
            current['owner'] = 'manager'
        if value is not None:
            current = {'owner': owner, 'text': value}
        path.write_text(json.dumps(current))
        return current

if name == 'python3':
    if len(sys.argv) > 1 and Path(sys.argv[1]).name == 'jarvis-reading-clipboard':
        import runpy
        scope = runpy.run_path(sys.argv[1], run_name='fixture_supervisor')
        class Desktop:
            def owner(self):
                return selection()['owner']
            def pid(self, window):
                return window if isinstance(window, int) else -1
            def clear_if_owner(self, window, pid):
                with (root / 'selection.lock').open('a') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    path = root / 'selection.json'
                    current = json.loads(path.read_text())
                    if os.environ['READING_CASE'] == 'race':
                        current = {'owner': 'external', 'text': 'New user copy'}
                    if current['owner'] == window == pid:
                        current = {'owner': None, 'text': ''}
                        (root / 'explicit-clear').touch()
                    path.write_text(json.dumps(current))
            def close(self): pass
        raise SystemExit(scope['supervise'](Desktop()))
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
elif name == 'xdotool':
    if sys.argv[1] == 'getactivewindow':
        print('123')
    elif 'ctrl+c' in sys.argv:
        selection('Selected test text', 'application')
elif name == 'xprop':
    print('WM_CLASS(STRING) = "DesktopEditors", "ONLYOFFICE"')
elif name == 'xclip':
    if '-i' not in sys.argv:
        print(selection()['text'], end='')
    elif '-silent' not in sys.argv and '-quiet' not in sys.argv:
        selection(sys.stdin.read(), 'external')
    else:
        text = sys.stdin.read()
        # Match xclip's real distinction: -silent forks; -quiet stays in the
        # foreground. A supervisor around silent mode must fail these tests.
        if '-silent' in sys.argv:
            reader, writer = os.pipe()
            if os.fork():
                os.close(writer)
                os.read(reader, 1)
                os.close(reader)
                raise SystemExit(0)
            os.close(reader)
            (root / 'pids' / str(os.getpid())).write_text(
                Path('/proc/self/stat').read_text().split(') ', 1)[1].split()[19])
        pid = os.getpid()
        if os.environ['READING_CASE'] == 'ignore-term':
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        else:
            def terminate(_signal, _frame):
                selection(release=pid)
                raise SystemExit(0)
            signal.signal(signal.SIGTERM, terminate)
        selection(text, pid)
        (root / 'owner-ready').write_text(str(pid))
        if '-silent' in sys.argv:
            os.write(writer, b'1')
            os.close(writer)
        while os.environ['READING_CASE'] == 'ignore-term' or selection()['owner'] == pid:
            time.sleep(0.02)
elif name == 'flatpak':
    (root / 'received.json').write_text(json.dumps(selection()['text']))
    # Remain alive like a launcher waiting for a reading task to finish.
    time.sleep(60)
elif name == 'gdbus':
    if os.environ['READING_CASE'] in ('crash', 'crash-replace', 'ignore-term'):
        (root / 'startup-hung').touch()
        time.sleep(60)
    print('(<4>,)')
'''


def wait_for(check, seconds, description):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.02)
    raise AssertionError(description)


def clipboard(environment, value=None):
    args = ['xclip', '-selection', 'clipboard', '-o' if value is None else '-i']
    result = subprocess.run(args, env=environment, input=value, text=True,
                            capture_output=True, timeout=2, check=True)
    return result.stdout


def alive_owner(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[0] != 'Z'
    except FileNotFoundError:
        return False


for case in ('accept', 'replace', 'replace-same', 'race', 'crash', 'crash-replace', 'ignore-term'):
    with tempfile.TemporaryDirectory(prefix='jarvis-reading-expiry-') as directory:
        root = Path(directory)
        home, peers, temporary = root / 'home', root / 'peers', root / 'temporary'
        for path in (home, peers, temporary, root / 'pids'):
            path.mkdir(mode=0o700)
        for name in ('python3', 'xclip', 'xdotool', 'xprop', 'flatpak', 'gdbus'):
            peer = peers / name
            peer.write_text('#!' + sys.executable + '\n' + PEER)
            peer.chmod(0o700)
        environment = dict(os.environ)
        environment.update(HOME=str(home), TMPDIR=str(temporary),
                           PATH=str(peers) + os.pathsep + os.environ['PATH'],
                           READING_FIXTURE=str(root), READING_CASE=case)
        process = subprocess.Popen(['bash', str(HELPER), 'selection', '1'],
                                   env=environment, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            wait_for(lambda: (root / 'owner-ready').exists(), 5, 'Owner did not start')
            wait_for(lambda: (root / 'received.json').exists(), 5, 'Reader did not receive request')
            assert json.loads((root / 'received.json').read_text()) == 'Selected test text'
            assert not list(temporary.iterdir()), 'Captured files persisted into reader startup'
            lock = home / '.local/state/jarvis/reading-speed.lock'
            owner = int((root / 'owner-ready').read_text())
            assert not (Path(f'/proc/{owner}/fd') / '9').exists(), 'Clipboard owner inherited reading lock'

            if case in ('replace', 'replace-same'):
                copied = 'Selected test text' if case == 'replace-same' else 'New user copy'
                clipboard(environment, copied)
                assert process.wait(timeout=5) == 0
                assert clipboard(environment) == copied, 'Cleanup erased a later copy'
                assert not (root / 'explicit-clear').exists()
            elif case == 'accept':
                assert process.wait(timeout=5) == 0
                assert clipboard(environment) == '', 'Normal cleanup retained selected text'
                assert (root / 'explicit-clear').exists(), 'Owner loss masked missing explicit clear'
            elif case == 'race':
                assert process.wait(timeout=5) == 0
                assert clipboard(environment) == 'New user copy', 'Atomic cleanup erased a racing copy'
            else:
                wait_for(lambda: (root / 'startup-hung').exists(), 5, 'Startup did not stall')
                assert clipboard(environment) == 'Selected test text'
                process.kill()  # Same direct-child SIGKILL used by subprocess.run on timeout.
                process.wait(timeout=2)
                if case == 'crash-replace':
                    clipboard(environment, 'New user copy')
                    wait_for(lambda: not alive_owner(owner), 3, 'Replaced owner remained alive')
                    assert clipboard(environment) == 'New user copy'
                else:
                    wait_for(lambda: clipboard(environment) == '', 18,
                             'Clipboard survived independent owner expiry')
                    assert (root / 'explicit-clear').exists()
                    wait_for(lambda: not alive_owner(owner), 2, 'Expired owner did not terminate')
            if case in ('accept', 'replace', 'replace-same', 'race'):
                subprocess.run(['flock', '-n', str(lock), '-c', 'true'], check=True, timeout=2)
            print('PASS:', case, 'clipboard ownership and cleanup')
        finally:
            # These are isolated fixture peers, not desktop applications.
            for pid_file in (root / 'pids').iterdir():
                pid = int(pid_file.name)
                try:
                    fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
                    if fields[19] == pid_file.read_text() and fields[0] != 'Z':
                        os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, FileNotFoundError):
                    pass
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)

print('PASS: cached-manager cleanup, later copies and independent expiry')
