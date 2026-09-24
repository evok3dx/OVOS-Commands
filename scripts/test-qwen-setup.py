#!/usr/bin/env python3
"""Offline checks for opt-in Qwen settings; no server or service is contacted."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("qwen_setup", Path(__file__).with_name("qwen-setup.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with TemporaryDirectory() as tmp:
    home = Path(tmp)
    config = home / ".config/mycroft/mycroft.conf"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"intents": {"pipeline": list(module.STAGES),
                                              "persona": {"handle_fallback": False}}}))
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def read(self): return json.dumps({"models": [{"name": module.MODEL}]}).encode()
    with patch.object(module, "urlopen", return_value=Response()):
        stages, ollama, model, saved, path = module.inspect(home)
    assert (stages, ollama, model, saved) == (True, True, True, {})
    module.enable(path, {"private_preference": "keep"})
    assert json.loads(path.read_text()) == {"private_preference": "keep", "version": 1,
                                              "mode": "on", "model": module.MODEL,
                                              "timeout_seconds": 8}
    assert path.stat().st_mode & 0o777 == 0o600
    original = path.read_bytes()
    try: module.enable(path, {"model": "another-user-model"})
    except ValueError: pass
    else: raise AssertionError("Must preserve a different configured model")
    assert path.read_bytes() == original
    module.enable(path, {"model": module.MODEL, "timeout_seconds": 15})
    assert json.loads(path.read_text())["timeout_seconds"] == 15
    try: module.enable(path, {"timeout_seconds": -1})
    except ValueError: pass
    else: raise AssertionError("Invalid saved model timeout accepted")
    config.write_text(json.dumps({"intents": {"pipeline": [],
                                              "persona": {"handle_fallback": True}}}))
    with patch.object(module, "urlopen", side_effect=OSError("offline")):
        assert module.inspect(home)[:3] == (False, False, False)
    # Missing Ollama must fail before touching private router settings.
    before = path.read_bytes()
    with (patch.object(module.os, "geteuid", return_value=1000),
          patch.object(module.Path, "home", return_value=home),
          patch.object(module, "urlopen", side_effect=OSError("offline")),
          patch("sys.argv", ["qwen-setup.py", "--prepare", "--yes"]),
          contextlib.redirect_stderr(io.StringIO())):
        try:
            module.main()
        except SystemExit as error:
            assert error.code == 2
        else:
            raise AssertionError("Missing Ollama was accepted")
    assert path.read_bytes() == before
print("PASS: local model gate, existing preference preservation and private atomic settings")
