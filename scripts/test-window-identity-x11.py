#!/usr/bin/env python3
"""Check real WM_CLASS discovery only on an explicitly isolated Xvfb display."""
import ctypes as C
import os
from pathlib import Path
import subprocess

if os.getuid() == 0 or os.environ.get('JARVIS_ISOLATED_X11_TEST') != '1':
    raise SystemExit('Run as an ordinary user under explicitly isolated Xvfb.')

ROOT = Path(__file__).resolve().parents[1]
x = C.CDLL('libX11.so.6')
x.XOpenDisplay.argtypes = [C.c_char_p]
x.XOpenDisplay.restype = C.c_void_p
x.XDefaultRootWindow.argtypes = [C.c_void_p]
x.XDefaultRootWindow.restype = C.c_ulong
x.XCreateSimpleWindow.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_int,
                                 C.c_uint, C.c_uint, C.c_uint, C.c_ulong, C.c_ulong]
x.XCreateSimpleWindow.restype = C.c_ulong
x.XInternAtom.argtypes = [C.c_void_p, C.c_char_p, C.c_int]
x.XInternAtom.restype = C.c_ulong
x.XChangeProperty.argtypes = [C.c_void_p, C.c_ulong, C.c_ulong, C.c_ulong,
                             C.c_int, C.c_int, C.POINTER(C.c_ubyte), C.c_int]
x.XStoreName.argtypes = [C.c_void_p, C.c_ulong, C.c_char_p]
x.XMapWindow.argtypes = [C.c_void_p, C.c_ulong]
x.XSync.argtypes = [C.c_void_p, C.c_int]
x.XDestroyWindow.argtypes = [C.c_void_p, C.c_ulong]
x.XCloseDisplay.argtypes = [C.c_void_p]

display = x.XOpenDisplay(None)
if not display:
    raise SystemExit('Isolated display is unavailable.')
root = x.XDefaultRootWindow(display)
windows = []

def atom(name):
    return x.XInternAtom(display, name.encode(), 0)

def property_value(window, name, kind, data, bits=8, count=None):
    x.XChangeProperty(display, window, atom(name), kind, bits, 0,
                      C.cast(data, C.POINTER(C.c_ubyte)),
                      len(data) if count is None else count)

def set_class(window, instance, class_name):
    data = (instance + '\0' + class_name + '\0').encode()
    property_value(window, 'WM_CLASS', 31, C.create_string_buffer(data), count=len(data))
    x.XSync(display, 0)

helper = (ROOT / 'system_helpers/jarvis-app-window').read_text()
assert helper.count('case "$action" in') == 1
discovery = helper.split('case "$action" in', 1)[0] + '\nfind_window\n'

def find(app):
    return subprocess.run(['bash', '-s', '--', 'probe', app], input=discovery,
                          capture_output=True, text=True, timeout=5)

try:
    for title in ('Proton Mail', 'Inbox'):
        window = x.XCreateSimpleWindow(display, root, 0, 0, 100, 100, 0, 0, 0)
        windows.append(window)
        x.XStoreName(display, window, title.encode())
        machine = C.create_string_buffer(b'fixture')
        property_value(window, 'WM_CLIENT_MACHINE', 31, machine, count=7)
        desktop = (C.c_ulong * 1)(0)
        property_value(window, '_NET_WM_DESKTOP', 6, desktop, 32, 1)
        x.XMapWindow(display, window)
    clients = (C.c_ulong * len(windows))(*windows)
    property_value(root, '_NET_CLIENT_LIST', 33, clients, 32, len(windows))
    set_class(windows[0], 'brave-browser', 'Brave-browser')
    set_class(windows[1], 'proton mail', 'Proton Mail')
    match = find('proton_mail')
    assert match.returncode == 0 and int(match.stdout.strip(), 16) == windows[1], match

    set_class(windows[1], 'fake-proton mail', 'Proton Mail Fake')
    match = find('proton_mail')
    assert match.returncode != 0 and not match.stdout.strip(), match

    set_class(windows[1], 'standard notes', 'Standard Notes')
    match = find('standard_notes')
    assert match.returncode == 0 and int(match.stdout.strip(), 16) == windows[1], match
    print('PASS: native X11 spaced class discovery and browser-title rejection')
finally:
    for window in windows:
        x.XDestroyWindow(display, window)
    x.XCloseDisplay(display)
