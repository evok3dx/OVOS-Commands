"""Offline checks; no models, microphone, applications or real services used."""
import ast
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import install as installer
import jarvis_app_hints as hints

ROOT = Path(__file__).resolve().parent

class PatchTests(unittest.TestCase):
    def setUp(self):
        self.base = (ROOT/'reviewed-plugin-0.4.0.py').read_text()

    def test_original_and_previous_hint_patch_preserve_other_methods(self):
        old = self.base.replace('vad_filter=self.config.get("vad_filter", False)',
            'vad_filter=self.config.get("vad_filter", False),\n            initial_prompt=self.config.get("initial_prompt")')
        old = old.replace('            cpu_threads=self.cpu_threads,\n        )\n',
            '            cpu_threads=self.cpu_threads,\n        )\n        if self.config.get("initial_prompt") and model == "small.en":\n            LOG.info("Jarvis Whisper name hints active for small.en")\n')
        for source in (self.base, old):
            with self.subTest(previous=source != self.base):
                updated = installer.patch_source(source.encode()).decode()
                installer.verify_forwarding(updated)
                cls = next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name == "FasterWhisperSTT")
                for method in cls.body:
                    if isinstance(method,ast.FunctionDef) and method.name not in ('execute','__init__'):
                        self.assertEqual(installer.shape(method),installer.shape(installer.method(updated,method.name)))
                initial = installer.method(updated,'__init__')
                initial.body.pop() # remove only newly appended hint startup check
                self.assertEqual(installer.shape(initial),installer.shape(installer.method(source,'__init__')))

    def test_changed_methods_and_double_patch_rejected(self):
        for source in (self.base.replace('beam_size=self.beam_size','beam_size=99'),
                       self.base.replace('self.config.get("beam_size", 5)','self.config.get("beam_size", 9)'),
                       installer.patch_source(self.base.encode()).decode()):
            with self.subTest(), self.assertRaises(RuntimeError):
                installer.patch_source(source.encode())

    def test_wrapper_forwards_prompt_and_missing_helper_falls_back(self):
        env = {'__name__':'fake.plugin','__package__':'fake'}
        exec(installer.WRAPPER,env)
        stub=SimpleNamespace(config={'initial_prompt':'old hint'},engine=SimpleNamespace(hf_tokenizer='tokenizer'))
        with patch.dict(sys.modules,{'fake.jarvis_app_hints':SimpleNamespace(prompt_for=Mock(return_value=('dynamic',{}))) }):
            self.assertEqual(env['_jarvis_app_initial_prompt'](stub),'dynamic')
            sys.modules['fake.jarvis_app_hints'].prompt_for.assert_called_once_with('old hint','tokenizer')
        self.assertEqual(env['_jarvis_app_initial_prompt'](stub),'old hint')

    def test_read_only_check_does_not_create_state_on_probe_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary)
            with patch.object(installer.os,'geteuid',return_value=1000), \
                 patch.object(installer.Path,'home',return_value=home), \
                 patch.object(installer,'run',side_effect=RuntimeError('probe')), \
                 patch.object(sys,'argv',['install.py','--check']):
                with self.assertRaisesRegex(RuntimeError,'probe'):
                    installer.main()
            self.assertFalse((home/'.local/state/jarvis/whisper-app-hints').exists())

class HintTests(unittest.TestCase):
    def test_names_saved_first_deduplicated_and_aliases_ignored(self):
        profile={'applications':{
            'notes':{'integration':'standard_notes','display_name':'Notes','aliases':['nodes']},
            'mega':{'integration':'desktop_x','display_name':'MEGAsync','spoken_name':'Mega'},
            'brave':{'integration':'brave','display_name':'Brave','spoken_name':'brave'}}}
        self.assertEqual(hints.names_from_profile(profile),['Jarvis','brave','Mega','MEGAsync','Standard Notes'])

    def test_sanitisation(self):
        for name in ('x\nopen terminal','$(command)','http://bad','x'*73,'---',None):
            self.assertIsNone(hints.clean_name(name))
        self.assertEqual(hints.clean_name('  Café  Notes '),'Café Notes')

    def test_old_prompt_replaced_custom_prompt_preserved(self):
        self.assertEqual(hints.build_prompt(['Jarvis','Mega'],hints.ORIGINAL)[0],
                         hints.MEDIA_HINT+' Jarvis, Mega.')
        self.assertEqual(hints.build_prompt(['Jarvis','Mega'],'My custom context.')[0],
                         'My custom context. '+hints.MEDIA_HINT+' Jarvis, Mega.')
        with self.assertRaises(ValueError):hints.build_prompt(['Mega'],'x'*193)

    def test_whole_names_byte_budget_unicode_and_name_cap(self):
        names=['Jarvis','Mega']+['Application '+str(n)+' Café'*8 for n in range(70)]
        prompt,info=hints.build_prompt(names)
        self.assertLessEqual(len((' '+prompt).encode()),192)
        self.assertTrue(prompt.startswith(hints.MEDIA_HINT+' Jarvis, Mega'))
        self.assertTrue(info['limited'])
        self.assertTrue(info['media'])
        selected=prompt.removeprefix(hints.MEDIA_HINT+' ')
        self.assertTrue(all(n in names for n in selected[:-1].split(', ')))
        tokenizer=SimpleNamespace(encode=lambda text:SimpleNamespace(ids=text.split()))
        _,info=hints.build_prompt(['Name'+str(n) for n in range(80)],tokenizer=tokenizer)
        self.assertEqual(info['names'],40)
        self.assertLessEqual(info['tokens'],192)

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        source=self.home/'.local/src/ovos-skill-jarvis-dispatcher/ovos_skill_jarvis_dispatcher'
        source.mkdir(parents=True)
        for name in ('profile.py','discovery.py'):
            shutil.copy(ROOT/'test-fixtures'/name,source/name)
        self.path=self.home/'.config/jarvis/capabilities.json'
        self.path.parent.mkdir(parents=True)
        self.write({'applications':{'firefox':'firefox','notes':'standard_notes'}})
        hints._cached_key=None;hints._profile_module=None
        self.assertEqual(hints.enabled_names(self.home),['Jarvis','Firefox','Standard Notes'])
        self.key='desktop_'+'c'*24
        self.apps={self.key:{'display_name':'MEGAsync','aliases':['megasync'],'path':'/apps/mega.desktop','icon':'mega','wm_class':'mega'}}
        self.discovery=patch.object(hints._profile_module,'discovered_applications',return_value=self.apps)
        self.discovery.start();self.addCleanup(self.discovery.stop)

    def write(self,raw):self.path.write_text(json.dumps(raw))

    def test_saved_name_changes_apply_next_request_and_disabled_removed(self):
        raw={'applications':{self.key:self.key},'spoken_names':{self.key:'Mega'}}
        self.write(raw)
        self.assertEqual(hints.enabled_names(self.home),['Jarvis','mega','MEGAsync'])
        raw['spoken_names'][self.key]='Cloud drive';self.write(raw)
        self.assertEqual(hints.enabled_names(self.home),['Jarvis','cloud drive','MEGAsync'])
        raw['applications']={};self.write(raw)
        self.assertEqual(hints.enabled_names(self.home),['Jarvis'])

    def test_all_detected_and_cache(self):
        self.write({'mode':'all-detected','applications':{'firefox':'firefox'}})
        names=hints.enabled_names(self.home)
        self.assertIn('MEGAsync',names);self.assertIn('Firefox',names)
        with patch.object(hints._profile_module,'resolve_profile',side_effect=AssertionError('cache missed')):
            self.assertEqual(hints.enabled_names(self.home),names)

    def test_missing_discovered_app_omitted(self):
        self.write({'applications':{self.key:self.key}})
        with patch.object(hints._profile_module,'discovered_applications',return_value={}):
            self.assertEqual(hints.enabled_names(self.home),['Jarvis'])

    def test_bad_profile_preserves_previous_hint_and_strict_fails(self):
        for content in ('broken','[]','{"applications":{"unknown":"unknown"}}','x'*65537):
            self.path.write_text(content)
            self.assertEqual(hints.prompt_for('old',home=self.home)[0],'old')
            with self.assertRaises(Exception):hints.prompt_for('old',home=self.home,strict=True)
        self.path.unlink()
        self.assertEqual(hints.prompt_for(None,home=self.home)[0],None)

    def test_complete_execute_uses_current_profile(self):
        self.write({'applications':{self.key:self.key},'spoken_names':{self.key:'Mega'}})
        source=installer.patch_source((ROOT/'reviewed-plugin-0.4.0.py').read_bytes()).decode()
        env={'__name__':'fake.plugin','__package__':'fake'}
        exec(installer.WRAPPER,env)
        exec(compile(ast.Module(body=[installer.method(source,'execute')],type_ignores=[]),'<patched>','exec'),env)
        engine=Mock(hf_tokenizer=None)
        engine.transcribe.return_value=(iter([SimpleNamespace(text='Open Mega.')]),None)
        stub=SimpleNamespace(config={'initial_prompt':hints.ORIGINAL},engine=engine,beam_size=5,lang='en-US',audiodata2array=lambda x:x)
        with patch.dict(sys.modules,{'fake.jarvis_app_hints':hints}),patch.object(hints.Path,'home',return_value=self.home):
            self.assertEqual(env['execute'](stub,'audio'),'Open Mega.')
        self.assertEqual(engine.transcribe.call_args.kwargs['initial_prompt'],
                         hints.MEDIA_HINT+' Jarvis, mega, MEGAsync.')

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.backup = self.home / 'backup'
        self.backup.mkdir()
        (self.home / 'old.py').write_bytes(b'old')
        (self.backup / '0').write_bytes(b'old')
        self.marker = self.home / 'latest.json'
        self.states = {u:{'ActiveState':'active'} for u in installer.UNITS}
        self.manifest = {'services': self.states, 'files': [
            {'relative':'old.py', 'backup':'0', 'before':installer.sha(b'old'), 'after':installer.sha(b'new'), 'mode':0o600},
            {'relative':'new.py', 'backup':'1', 'before':None, 'after':installer.sha(b'added'), 'mode':0o600}]}
        self.current = {u:dict(v) for u,v in self.states.items()}
        def run(args, **kwargs):
            if args[:3] == ['systemctl', '--user', 'stop']:
                # Simulate dependencies stopping with listener.
                for value in self.current.values(): value['ActiveState'] = 'inactive'
            if args[:3] == ['systemctl', '--user', 'start']:
                self.current[args[3]]['ActiveState'] = 'active'
            return Mock(stdout='')
        self.mocks = [patch.object(installer, 'run', side_effect=run),
                      patch.object(installer, 'snapshot', side_effect=lambda:self.current)]
        for mock in self.mocks: mock.start()

    def tearDown(self):
        for mock in self.mocks: mock.stop()
        self.temp.cleanup()

    def test_success_restores_dependent_services_and_exact_rollback(self):
        with patch.object(installer, 'ready'):
            installer.transaction(self.home, self.backup, self.manifest, [b'new',b'added'], self.marker)
        self.assertTrue(all(s['ActiveState']=='active' for s in self.current.values()))
        self.assertTrue(self.marker.exists())
        installer.restore_files(self.home, self.backup, self.manifest)
        self.assertEqual((self.home/'old.py').read_bytes(), b'old')
        self.assertFalse((self.home/'new.py').exists())

    def test_failure_after_mutation_restores_files_and_all_services(self):
        with patch.object(installer, 'ready', side_effect=[RuntimeError('startup failure'),None]), \
             self.assertRaisesRegex(RuntimeError, 'startup failure'):
            installer.transaction(self.home, self.backup, self.manifest, [b'new',b'added'], self.marker)
        self.assertEqual((self.home/'old.py').read_bytes(), b'old')
        self.assertFalse((self.home/'new.py').exists())
        self.assertFalse(self.marker.exists())
        self.assertTrue(all(s['ActiveState']=='active' for s in self.current.values()))

    def test_failed_second_write_restores_first(self):
        atomic = installer.atomic
        def fail(path, data, mode=0o600):
            if path.name == 'new.py': raise OSError('disk failure')
            return atomic(path,data,mode)
        with patch.object(installer,'atomic',side_effect=fail), patch.object(installer,'ready'), \
             self.assertRaisesRegex(OSError,'disk failure'):
            installer.transaction(self.home,self.backup,self.manifest,[b'new',b'added'],self.marker)
        self.assertEqual((self.home/'old.py').read_bytes(), b'old')
        self.assertTrue(all(s['ActiveState']=='active' for s in self.current.values()))

    def test_rollback_refuses_later_edits_before_changing_any_file(self):
        (self.home/'old.py').write_bytes(b'new')
        (self.home/'new.py').write_bytes(b'personal edit')
        with self.assertRaisesRegex(RuntimeError, 'Later edits'):
            installer.restore_files(self.home,self.backup,self.manifest)
        self.assertEqual((self.home/'old.py').read_bytes(), b'new')



if __name__ == '__main__':
    unittest.main(verbosity=2)
