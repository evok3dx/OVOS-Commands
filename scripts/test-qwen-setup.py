#!/usr/bin/env python3
"""Offline checks for opt-in Qwen settings; no server or service is contacted."""
import ast
import importlib.util
import contextlib
import io
import json
import time
import types
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

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
    # Guided setup must pull the exact required model and re-check it before
    # returning success. This is the V2/V3 installer-parity release gate.
    with (patch.object(module.os, "geteuid", return_value=1000),
          patch.object(module.Path, "home", return_value=home),
          patch.object(module.shutil, "which", return_value="/usr/bin/ollama"),
          patch.object(module, "inspect", side_effect=[
              (True, True, False, {}, path),
              (True, True, True, {}, path),
          ]),
          patch.object(module.subprocess, "run", return_value=Mock(returncode=0)) as pull,
          patch("sys.argv", ["qwen-setup.py", "--prepare", "--yes"])):
        module.main()
    pull.assert_called_once_with(["ollama", "pull", module.MODEL], check=False)
    for code in (1, 130):
        before = path.read_bytes()
        feedback = io.StringIO()
        with (patch.object(module.os, "geteuid", return_value=1000),
              patch.object(module.Path, "home", return_value=home),
              patch.object(module.shutil, "which", return_value="/usr/bin/ollama"),
              patch.object(module, "inspect", return_value=(True, True, False, {}, path)),
              patch.object(module.subprocess, "run", return_value=Mock(returncode=code)),
              patch("sys.argv", ["qwen-setup.py", "--prepare", "--yes"]),
              contextlib.redirect_stderr(feedback)):
            try:
                module.main()
            except SystemExit as error:
                assert error.code == 1
            else:
                raise AssertionError("Failed model pull was accepted")
        assert path.read_bytes() == before
        assert "No router settings changed" in feedback.getvalue()
        assert "Traceback" not in feedback.getvalue()
print("PASS: local model gate, existing preference preservation and private atomic settings")

# An explicit off preference survives both ordinary and isolated installer
# paths, while an explicit owner enable remains available. No daemon call is
# necessary just to preserve Off or disable AI.
with TemporaryDirectory() as tmp:
    home = Path(tmp)
    path = home / '.config/jarvis/router.json'
    module.enable(path, {'backend': 'jarvis', 'private_preference': 'keep'})
    on = json.loads(path.read_text())
    module.disable(path, on)
    off = json.loads(path.read_text())
    assert off == dict(on, mode='off')
    assert path.stat().st_mode & 0o777 == 0o600
    before = path.read_bytes()
    for arguments in (['--enable', '--keep-disabled'], ['--disable']):
        with (patch.object(module.os, 'geteuid', return_value=1000),
              patch.object(module.Path, 'home', return_value=home),
              patch.object(module, 'inspect', side_effect=AssertionError('Off contacted Ollama')),
              patch('sys.argv', ['qwen-setup.py', *arguments])):
            module.main()
        assert path.read_bytes() == before
    # Invalid documents must not be silently replaced by an empty dictionary.
    for raw in ('[]', '{', 'x' * 4097):
        path.write_text(raw)
        try:
            module.read_saved(path)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid router settings accepted')
        assert path.read_text() == raw
    path.unlink()
    destination = home / 'owner.json'
    destination.write_text('{"private":"keep"}')
    path.symlink_to(destination)
    try:
        module.disable(path, off)
    except ValueError:
        pass
    else:
        raise AssertionError('A router symlink was replaced')
    assert destination.read_text() == '{"private":"keep"}'
    path.unlink()
    module.write_settings(path, off)
    with patch.object(module.os, 'replace', side_effect=OSError('fixture')):
        try:
            module.enable(path, off)
        except OSError:
            pass
        else:
            raise AssertionError('Write failure was ignored')
    assert json.loads(path.read_text()) == off
    assert not list(path.parent.glob('.router-*'))

    control_spec = importlib.util.spec_from_file_location(
        'ai_settings_control', Path(__file__).with_name('control_runtime.py'))
    control = importlib.util.module_from_spec(control_spec)
    control_spec.loader.exec_module(control)
    import isolation_install
    with (patch.object(module.Path, 'home', return_value=home),
          patch.object(control, '_qwen_settings_module', return_value=module),
          patch.object(isolation_install, 'installation_blocked', return_value=False),
          patch.object(module.subprocess, 'run', side_effect=AssertionError('Setting controlled a service')),
          patch.object(module, 'inspect', return_value=(True, True, True, off, path)) as inspect_gate):
        assert control.ai_fallback_status() == {'enabled': False, 'model': module.MODEL}
        assert control.set_ai_fallback(True)['enabled']
        assert inspect_gate.call_count == 1
        assert json.loads(path.read_text())['private_preference'] == 'keep'
        assert control.set_ai_fallback(False)['enabled'] is False
        assert inspect_gate.call_count == 1, 'Disabling must not contact the model'
        assert control.ai_fallback_status()['enabled'] is False
        runtime_tree = ast.parse((Path(__file__).resolve().parents[1] /
                                  'ovos_skill_jarvis_dispatcher/routing_runtime.py').read_text())
        runtime_class = next(node for node in runtime_tree.body
                             if isinstance(node, ast.ClassDef) and node.name == 'RouterRuntime')
        nodes = [node for node in runtime_tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == 'settings']
        nodes += [node for node in runtime_class.body
                  if isinstance(node, ast.FunctionDef) and node.name in ('propose', 'valid')]
        scope = {'Path': Path, 'json': json, 'time': time,
                 'classify': Mock(side_effect=AssertionError('Disabled AI reached the model'))}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'production-ai-off-guards', 'exec'), scope)
        skill = types.SimpleNamespace(_message_generation=0)
        runtime = types.SimpleNamespace(skill=lambda: skill, cancel=Mock(), closed=False,
                                        busy=lambda owner: False, epoch=0)
        assert scope['settings']() is False
        assert scope['propose'](runtime, 'open Firefox') is None
        assert not scope['valid'](runtime, {'epoch': 0, 'generation': 0,
                                           'expires': time.monotonic() + 60}, skill)
        scope['classify'].assert_not_called()
        before = path.read_bytes()
        inspect_gate.return_value = (True, False, False, off, path)
        try:
            control.set_ai_fallback(True)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Unavailable model was enabled')
        assert path.read_bytes() == before
        with patch.object(isolation_install, 'installation_blocked', return_value=True):
            try:
                control.set_ai_fallback(True)
            except RuntimeError:
                pass
            else:
                raise AssertionError('Recovery guard was ignored')
        assert path.read_bytes() == before

root = Path(__file__).resolve().parents[1]
assert 'qwen-setup.py" --enable --keep-disabled' in (root / 'scripts/install.sh').read_text()
assert "'--enable', '--keep-disabled'" in (root / 'scripts/isolation_install.py').read_text()
print('PASS: AI GUI settings gate, private atomic disable/enable and saved Off across both installers')
