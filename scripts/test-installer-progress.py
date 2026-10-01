#!/usr/bin/env python3
"""Progress reports actual work, retains heartbeat and announces failures."""
import io
import os
import threading
from unittest.mock import patch
from installer_progress import Progress

assert os.getuid()!=0, 'Run as the ordinary user'
class Stream(io.StringIO):
    def __init__(self):super().__init__();self.heartbeat=threading.Event()
    def isatty(self):return True
    def write(self,text):
        if 'still working' in text:self.heartbeat.set()
        return super().write(text)
stream=Stream()
with patch.dict(os.environ,{},clear=True):
    with Progress('Download',stream=stream,interval=0.01) as progress:
        assert stream.heartbeat.wait(1)
        progress.fraction(5,100);progress.fraction(6,100);progress.fraction(50,100)
    assert '\033[32m' in stream.getvalue() and '50%' in stream.getvalue()
    assert '100%' not in stream.getvalue() and stream.getvalue().count('5%')==1
assert not progress.thread.is_alive()
plain=io.StringIO()
try:
    with Progress('Verify',stream=plain) as failed:
        failed.fraction(1,10)
        raise RuntimeError('fixture')
except RuntimeError:pass
assert 'failed' in plain.getvalue() and 'complete' not in plain.getvalue()
assert '\033' not in plain.getvalue() and not failed.thread.is_alive()
print('PASS: measured green CLI progress, quiet non-TTY output, slow-step heartbeat and failure cleanup')
