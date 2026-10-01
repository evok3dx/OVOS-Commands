"""Ordinary-user entry points for reviewed V4 system-manager service data."""
import argparse
from copy import deepcopy
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
from functools import wraps

COMPONENTS=('core','listener','audio','weather','media')
ONLINE_SKILLS=tuple('ovos-skill-'+name+'.openvoiceos' for name in
                    ('weather','jarvis-media','ddg','wolfie','wikipedia','wikihow','ip','speedtest')) + ('skill-ovos-wallpapers.openvoiceos',)
ONLINE_STAGES={'ovos-common-query-pipeline-plugin','ovos-persona-pipeline-plugin','ovos-ocp-pipeline-plugin',
               'common_qa','ocp_high','ocp_medium','ocp_low','ocp_legacy'}
BOOT_SOURCE_SHA256='1bc356474e0d970fdd7955b5e2592a4c053178c1c1f2e8c2aa075e7b8e0d1a5b'
PADACIOSO_SOURCE_SHA256='645edc74b0711bc9d0547e8c809acea6ae0b24ad61f38528d48fc1a49fdab02c'


def install_intent_cleanup():
    """Serialize reviewed Padacioso mutations; repeated detach stays idempotent."""
    import padacioso.opm as engine
    if hashlib.sha256(Path(engine.__file__).read_bytes()).hexdigest()!=PADACIOSO_SOURCE_SHA256:
        raise RuntimeError('Intent cleanup source differs from the reviewed runtime')
    cls=engine.PadaciosoPipeline
    if getattr(cls,'_jarvis_cleanup_installed',False):return
    lock=threading.RLock()
    def guarded(function):
        @wraps(function)
        def call(self,*args,**kwargs):
            with lock:return function(self,*args,**kwargs)
        return call
    for name in ('register_intent','register_entity','handle_register_template',
                 'handle_register_entity','handle_detach_intent','handle_detach_skill',
                 'handle_deregister_intent','handle_deregister_entity',
                 'handle_deregister_skill','handle_disable_intent','handle_enable_intent',
                 '_PadaciosoPipeline__detach_intent','_PadaciosoPipeline__detach_entity'):
        setattr(cls,name,guarded(getattr(cls,name)))
    cls._jarvis_cleanup_installed=True


def install_boot_readiness():
    """Adapt the exact reviewed boot skill in memory, without editing settings.

    Readiness still comes from each service's bus response. Cancel the running
    callback on shutdown so the emitter executor cannot wait for absent skills.
    """
    import ovos_skill_boot_finished as boot
    if hashlib.sha256(Path(boot.__file__).read_bytes()).hexdigest()!=BOOT_SOURCE_SHA256:
        raise RuntimeError('Boot readiness source differs from the reviewed runtime')
    cls=boot.BootFinishedSkill
    if getattr(cls,'_jarvis_readiness_installed',False):return
    initialize,shutdown,announce=cls.initialize,cls.shutdown,cls.handle_ready
    check=cls.check_services_ready

    def initialise(self):
        self._jarvis_ready_stop=threading.Event()
        self._jarvis_ready_check=threading.Lock()
        self._jarvis_ready_announce=threading.Lock()
        self._jarvis_ready_confirmed=False
        self._jarvis_ready_announced=False
        initialize(self)

    def ready(self):
        if 'ready_settings' in self.settings:
            names=self.settings['ready_settings']  # Preserve explicit owner policy.
        else:
            blocked=self.config_core.get('skills',{}).get('blacklisted_skills',[])
            names=['skills','voice','audio',*[name for name in
                   boot.get_installed_skill_ids(self.config_core) if name not in blocked]]
        services=dict.fromkeys(names,False)
        deadline=time.monotonic()+60
        while not self._jarvis_ready_stop.is_set():
            for name,done in services.items():
                if self._jarvis_ready_stop.is_set():return False
                if not done:
                    # Keep the upstream response semantics. Check cancellation
                    # between individual bounded bus waits, not after the list.
                    services[name]=check(self,{name:False})
                if time.monotonic()>=deadline and not all(services.values()):return False
            if self._jarvis_ready_stop.is_set():return False
            if all(services.values()):return True
            if self._jarvis_ready_stop.wait(min(3,max(0,deadline-time.monotonic()))):return False
        return False

    def check_readiness(self,message=None):
        if self._jarvis_ready_stop.is_set() or not self._jarvis_ready_check.acquire(blocking=False):return
        event=None
        try:
            if self._jarvis_ready_announced:return
            if ready(self):
                with self._jarvis_ready_announce:
                    if self._jarvis_ready_stop.is_set():return
                    self._jarvis_ready_confirmed=True
                    event='mycroft.ready'
            elif not self._jarvis_ready_stop.wait(5):
                event='mycroft.ready.check'
        finally:self._jarvis_ready_check.release()
        # Release the coalescing lock before dispatching the next check; a fast
        # emitter must not drop the retry because this callback still holds it.
        if event and not self._jarvis_ready_stop.is_set():self.bus.emit(boot.Message(event))

    def announce_ready(self,message):
        with self._jarvis_ready_announce:
            if (self._jarvis_ready_stop.is_set() or not self._jarvis_ready_confirmed
                    or self._jarvis_ready_announced):return
            self._jarvis_ready_announced=True
        announce(self,message)  # Retains speak_ready / ready_sound choices.

    original_acknowledge=getattr(cls,'acknowledge',None)
    def acknowledge(self):
        configured=self.config_core.get('sounds',{}).get('acknowledge','snd/acknowledge.mp3')
        cue=Path.home()/'.local/share/ovos/sounds/jarvis-ready.wav'
        if configured=='snd/acknowledge.mp3' and cue.is_file():
            self.play_audio(str(cue),instant=True)
        elif original_acknowledge is not None:
            original_acknowledge(self)

    def stop(self):
        self._jarvis_ready_stop.set()
        return shutdown(self)

    cls.initialize=initialise
    cls.is_device_ready=ready
    cls.handle_check_device_readiness=check_readiness
    cls.handle_ready=announce_ready
    cls.acknowledge=acknowledge
    cls.shutdown=stop
    cls._jarvis_readiness_installed=True


def worker_identity(component,uid,gid):
    if (component not in COMPONENTS or type(uid) is not int or type(gid) is not int or uid<=0 or gid<=0
            or (os.getuid(),os.geteuid(),os.getgid(),os.getegid())!=(uid,uid,gid,gid)):
        raise RuntimeError('Worker must run as the ordinary desktop user/group')
    props=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    if int(props.get('CapEff','-1').strip(),16) or props.get('NoNewPrivs','').strip()!='1':
        raise RuntimeError('Worker privileges need review')
    expected=f'0::/system.slice/jarvis-v4-{uid}-{component}.service'
    if expected not in Path('/proc/self/cgroup').read_text().splitlines():
        raise RuntimeError('Worker is outside its reviewed service cgroup')


def verify_pins():
    root=Path(__file__).resolve().parents[1]
    inventory=root/'voice/runtime-linux-x86_64-py311.json'
    lock=root/'voice/runtime-wheels-linux-x86_64-py311.txt'
    pins=json.loads(inventory.read_text())['packages']
    for name in pins:
        if metadata.version(name)!=pins[name]:raise RuntimeError('Stage the reviewed V4 runtime before isolation')
    from runtime_provenance import matches
    if not matches(Path(sys.prefix),inventory,lock):
        raise RuntimeError('A verified full-runtime installation receipt is required before isolation')


def overlay(config,component):
    """Preserve disk settings; enforce known online ownership on every reload."""
    value=deepcopy(config)
    if component=='core':
        skills=value.setdefault('skills',{})
        blocked=skills.get('blacklisted_skills',[])
        if not isinstance(blocked,list) or not all(isinstance(s,str) for s in blocked):
            raise ValueError('Custom skill blacklist needs review')
        skills['blacklisted_skills']=list(dict.fromkeys([*blocked,*ONLINE_SKILLS]))
        intents=value.setdefault('intents',{})
        stages=intents.get('pipeline',[])
        if not isinstance(stages,list) or not all(isinstance(s,str) for s in stages):
            raise ValueError('Custom intent pipeline needs review')
        intents['pipeline']=[s for s in stages if s not in ONLINE_STAGES
                            and re.sub(r'-(?:high|medium|low|legacy)$','',s) not in ONLINE_STAGES]
    expected={'listener':('stt','ovos-stt-plugin-fasterwhisper'),'audio':('tts','ovos-tts-plugin-phoonnx')}
    if component in expected:
        category,module=expected[component]
        if value.get(category,{}).get('module')!=module:
            raise ValueError('Isolation requires the reviewed local voice configuration')
    return value


def install_overlay(component):
    from ovos_config import Configuration
    original=Configuration.filter_and_merge
    remote_allowed=False
    def merge(configs):
        nonlocal remote_allowed
        value=original(configs)
        result=overlay(value,component)
        if component=='core':
            blocked=value.get('skills',{}).get('blacklisted_skills',[])
            remote_allowed='ovos-skill-jarvis-media.openvoiceos' not in blocked
            # Do not import skills inside Configuration's initial load; that
            # can recursively request configuration while it is being built.
            bridge=sys.modules.get('ovos_skill_jarvis_media.bridge')
            if bridge is not None:bridge.enable_remote(remote_allowed)
        return result
    Configuration.filter_and_merge=staticmethod(merge)
    Configuration.load_all_configs()
    if component=='core':
        from ovos_skill_jarvis_media.bridge import enable_remote
        enable_remote(remote_allowed)


def run_component(component):
    if component in {'weather','media'}:
        from ovos_config import Configuration
        from ovos_workshop.skill_launcher import SkillContainer
        skill_id='ovos-skill-'+('weather' if component=='weather' else 'jarvis-media')+'.openvoiceos'
        if skill_id in Configuration().get('skills',{}).get('blacklisted_skills',[]):
            return  # Retain the owner's explicit disabled-skill choice.
        container=SkillContainer(skill_id)
        container.skill_directory=None
        container.run()
    elif component=='core':
        install_intent_cleanup()
        install_boot_readiness()
        from ovos_core.__main__ import main
        main(enable_installer=False)
    elif component=='listener':
        from ovos_dinkum_listener.__main__ import main
        main()
    elif component=='audio':
        from ovos_audio.__main__ import main
        main()


def main():
    from isolation_install import installation_blocked
    if installation_blocked():
        raise RuntimeError('Managed installation is incomplete; isolated workers remain stopped for recovery')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component',choices=COMPONENTS)
    parser.add_argument('--uid',type=int,required=True)
    parser.add_argument('--gid',type=int,required=True)
    args=parser.parse_args()
    worker_identity(args.component,args.uid,args.gid)
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    verify_pins()
    for key in tuple(os.environ):
        if key.lower().endswith('_proxy'):os.environ.pop(key,None)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    install_overlay(args.component)
    if args.component=='weather':
        from weather_boundary import install
        install()
    from verify_core_isolation import attach
    bus=attach(args.component,args.uid,args.gid)
    try:run_component(args.component)
    finally:
        if bus is not None:bus.close()


if __name__=='__main__':main()
