#!/usr/bin/env python3
"""Source guard and concurrent detach on the exact pinned Padacioso method."""
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
from unittest.mock import patch
import zipfile
import isolation_worker as worker

assert os.getuid()!=0, 'Run as the ordinary user'
NAMES=('register_intent','register_entity','handle_register_template','handle_register_entity',
       'handle_detach_intent','handle_detach_skill','handle_deregister_intent',
       'handle_deregister_entity','handle_deregister_skill','handle_disable_intent',
       'handle_enable_intent','_PadaciosoPipeline__detach_intent','_PadaciosoPipeline__detach_entity')
def no_op(self,*args,**kwargs):pass
class Fixture:
    pass
for name in NAMES:setattr(Fixture,name,no_op)
engine=types.SimpleNamespace(__file__=__file__,PadaciosoPipeline=Fixture)
with patch.dict(sys.modules,{'padacioso':types.SimpleNamespace(opm=engine),'padacioso.opm':engine}):
    try:worker.install_intent_cleanup()
    except RuntimeError:pass
    else:raise AssertionError('Unknown Padacioso source accepted')
    with patch.object(worker,'PADACIOSO_SOURCE_SHA256',hashlib.sha256(Path(__file__).read_bytes()).hexdigest()):
        worker.install_intent_cleanup();worker.install_intent_cleanup()
print('PASS: cleanup adapter rejects unknown source and installs once')

if len(sys.argv)==2:
    root=Path(__file__).resolve().parents[1]
    record=json.loads((root/'voice/runtime-wheels-linux-x86_64-py311.artifacts.json').read_text())['packages']['padacioso']
    wheel=Path(sys.argv[1]);assert hashlib.sha256(wheel.read_bytes()).hexdigest()==record['sha256']
    with zipfile.ZipFile(wheel) as archive:source=archive.read('padacioso/opm.py')
    assert hashlib.sha256(source).hexdigest()==worker.PADACIOSO_SOURCE_SHA256
    tree=ast.parse(source)
    original=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PadaciosoPipeline')
    method=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='__detach_intent')
    class_node=ast.ClassDef(name='PadaciosoPipeline',bases=[],keywords=[],body=[method],decorator_list=[])
    scope={'_dealias_intent_name':lambda name:name.removesuffix('.intent'),
           '_calc_padacioso_intent':types.SimpleNamespace(cache_clear=lambda:None)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[class_node],type_ignores=[])),
                 'exact-reviewed-padacioso-detach','exec'),scope)
    cls=scope['PadaciosoPipeline']
    for name in NAMES:
        if not hasattr(cls,name):setattr(cls,name,no_op)
    def prepare():
        obj=cls();obj.registered_intents=['skill:one'];obj._intent_slot_blacklists={}
        obj._intent_slot_types={};obj._intent_context_gates={'skill:one':'gate'}
        entered=threading.Event();second=threading.Event();release=threading.Event()
        calls=[]
        class Container:
            intent_samples={'skill:one':[]}
            def remove_intent(self,name):
                calls.append(name)
                if len(calls)==1:entered.set()
                else:second.set()
                assert release.wait(2)
                self.intent_samples.pop(name,None)
        obj.containers={'en-US':Container()}
        return obj,entered,second,release,calls
    # Reproduce the upstream check/remove race with its unmodified method.
    obj,entered,second,release,calls=prepare()
    with ThreadPoolExecutor(max_workers=2) as executor:
        one=executor.submit(obj._PadaciosoPipeline__detach_intent,'skill:one')
        assert entered.wait(2)
        two=executor.submit(obj._PadaciosoPipeline__detach_intent,'skill:one')
        assert second.wait(2);release.set()
        errors=[]
        for future in (one,two):
            try:future.result(timeout=2)
            except ValueError as error:errors.append(str(error))
        assert errors==['list.remove(x): x not in list']
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'opm.py';path.write_bytes(source)
        engine=types.SimpleNamespace(__file__=str(path),PadaciosoPipeline=cls)
        with patch.dict(sys.modules,{'padacioso':types.SimpleNamespace(opm=engine),'padacioso.opm':engine}):
            worker.install_intent_cleanup()
        obj,entered,second,release,calls=prepare()
        with ThreadPoolExecutor(max_workers=2) as executor:
            one=executor.submit(obj._PadaciosoPipeline__detach_intent,'skill:one')
            assert entered.wait(2)
            two=executor.submit(obj._PadaciosoPipeline__detach_intent,'skill:one.intent')
            assert not second.wait(0.05);release.set()
            one.result(timeout=2);two.result(timeout=2)
        assert calls==['skill:one'] and not obj.registered_intents and not obj._intent_context_gates
        obj._PadaciosoPipeline__detach_intent('skill:one')
        # A language-scoped detach must preserve bookkeeping for other langs.
        obj.registered_intents=['skill:one'];obj._intent_context_gates={'skill:one':'gate'}
        obj.containers['fr-FR']=types.SimpleNamespace(intent_samples={'skill:one':[]})
        obj._PadaciosoPipeline__detach_intent('skill:one','en-US')
        assert obj.registered_intents==['skill:one'] and obj._intent_context_gates
    print('PASS: exact pinned method reproduces race; guarded concurrent/repeated/alias detach and language preservation')
