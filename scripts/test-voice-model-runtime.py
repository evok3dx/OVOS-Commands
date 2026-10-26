#!/usr/bin/env python3
"""Actual retained-runtime inference after removing a disposable cache fixture.

Run only in an isolated test home; never remove a real account's cache.
"""
import os
from pathlib import Path
import shutil
import tempfile
import wave

import voice_models

if os.getuid() == 0 or os.environ.get('JARVIS_ISOLATED_MODEL_TEST') != '1':
    raise SystemExit('Use an ordinary-user isolated model-test home.')

home = Path.home()
if (not home.name.startswith('jarvis-model-home.')
        or (home / '.jarvis-model-test-home').read_text() != 'isolated speech model test\n'):
    raise SystemExit('Missing isolated model-test home marker.')

voice_models.prepare(home)
disposable = home / '.cache'
if disposable.is_symlink():
    raise SystemExit('Disposable fixture must not be a link.')
shutil.rmtree(disposable, ignore_errors=True)
voice_models.configure_environment(home)
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

from faster_whisper import WhisperModel
model = WhisperModel('small.en', device='cpu', compute_type='int8', cpu_threads=2,
                     local_files_only=True)
import numpy as np
segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32), language='en',
                               beam_size=1, vad_filter=True)
list(segments)
del model
print('PASS: actual Whisper loads and transcribes offline after disposable cache deletion.')

from phoonnx.opm import PhoonnxTTSPlugin
tts = PhoonnxTTSPlugin(config={'lang': 'en-US', 'voice': 'kokoro/af_bella',
                              'onnx_providers': ['CPUExecutionProvider']})
with tempfile.TemporaryDirectory(prefix='speech-proof-', dir=home) as folder:
    target = Path(folder) / 'proof.wav'
    tts.get_tts('Ready.', str(target), lang='en-US', voice='kokoro/af_bella')
    with wave.open(str(target), 'rb') as output:
        assert output.getnframes() > 0 and output.getframerate() > 0
assert not voice_models.inspect(home)
print('PASS: actual Bella synthesises a nonempty WAV offline after disposable cache deletion.')
