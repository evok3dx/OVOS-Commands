#!/usr/bin/env python3
"""The downstream wake plugin cannot select TFLite or download at startup."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'extras/ovos-ww-plugin-openwakeword-onnx'
provenance=json.loads((source/'PROVENANCE.json').read_text())
for name,digest in provenance['source_files_sha256'].items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
assert provenance['downstream_version']=='0.4.5a2+jarvis.1'

calls=[]
class Base:
    def __init__(self,key_phrase,config):self.config=config or {}
def paths(inference_framework):
    assert inference_framework=='onnx'
    return ['/reviewed/hey_jarvis_v0.1.onnx']
class Model:
    def __init__(self,**kwargs):
        calls.append(kwargs)
        assert kwargs['inference_framework']=='onnx'
        self.models={'hey_jarvis':object()}
engine=types.ModuleType('openwakeword');engine.Model=Model;engine.get_pretrained_model_paths=paths
hotwords=types.ModuleType('ovos_plugin_manager.templates.hotwords');hotwords.HotWordEngine=Base
modules={'numpy':types.ModuleType('numpy'),'openwakeword':engine,
         'ovos_plugin_manager.templates.hotwords':hotwords}
with patch.dict(sys.modules,modules):
    spec=importlib.util.spec_from_file_location('reviewed_onnx_wake',source/'ovos_ww_plugin_openwakeword/__init__.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    plugin=module.OwwHotwordPlugin()
    assert calls[-1]['wakeword_models']==['/reviewed/hey_jarvis_v0.1.onnx']
    for config in ({'inference_framework':'tflite'}, {'models':['/reviewed/hey_jarvis.tflite']}, {'models':[]}):
        count=len(calls)
        try:module.OwwHotwordPlugin(config=config)
        except ValueError:pass
        else:raise AssertionError('Unsafe/missing backend model accepted')
        assert len(calls)==count

print('PASS: reviewed source identity, ONNX-only selection and pre-model TFLite refusal')
