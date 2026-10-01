#!/usr/bin/env python3
"""Collect bounded V4 laptop evidence without install, restart or external requests."""
import argparse
import configparser
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
QWEN = 'qwen3:4b-instruct-2507-q4_K_M'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-','_'), ROOT/'scripts'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_mapping(path):
    try:
        if path.stat().st_size > 1024*1024:
            return {}
        value = json.loads(path.read_text())
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):
        return {}


def settings(home):
    # Read only literal local configuration; do not instantiate OVOS plugins.
    config = read_mapping(home/'.config/mycroft/mycroft.conf')
    bus = config.get('websocket',{})
    bus = bus if isinstance(bus,dict) else {}
    host = bus.get('host')
    listener = config.get('listener',{})
    listener = listener if isinstance(listener,dict) else {}
    def module_matches(section, expected):
        value = config.get(section,{})
        return isinstance(value,dict) and value.get('module') == expected
    launcher = home/'.local/bin/hermes-secure-launch'
    try:
        text = launcher.read_text() if launcher.stat().st_size <= 65536 else ''
    except OSError:
        text = ''
    podman = Path(f'/run/user/{os.getuid()}/podman/podman.sock')
    return {
        'configuration_basis':'literal user file only; effective merged defaults not verified',
        'bus_host_explicit':host is not None,
        'bus_host_explicitly_loopback':host in ('127.0.0.1','::1','localhost'),
        'stt_matches_reviewed':module_matches('stt','ovos-stt-plugin-fasterwhisper'),
        'tts_matches_reviewed':module_matches('tts','ovos-tts-plugin-phoonnx'),
        'wake_is_default':listener.get('wake_word') == 'hey_jarvis',
        'hermes_launcher_found':bool(text),
        'hermes_setuid_sandbox_exception_present':'--disable-setuid-sandbox' in text,
        'hermes_podman_socket_reference_present':'podman.sock' in text,
        'podman_socket_present':podman.exists(),
        'hermes_effective_tool_permissions_verified':False,
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError('Loopback model inventory cannot redirect')


def model_identity(home):
    router = read_mapping(home/'.config/jarvis/router.json')
    configured = router.get('model',QWEN)
    value = {'request_boundary':'fixed loopback GET only; no proxy or redirects',
             'reviewed_model_configured':configured == QWEN,
             'available':False,'digest_recorded':False,'files_verified':False,
             'upstream_authenticity_verified':False}
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        from model_endpoint import model_port
        with opener.open(f'http://127.0.0.1:{model_port(home)}/api/tags',timeout=2) as response:
            raw = response.read(1024*1024+1)
        if len(raw)>1024*1024:
            return value
        models = json.loads(raw).get('models',[])
        for model in models:
            if isinstance(model,dict) and model.get('name') == configured:
                value['available'] = True
                digest = model.get('digest')
                if isinstance(digest,str) and re.fullmatch(r'(?:sha256:)?[a-f0-9]{64}',digest):
                    value.update(digest_recorded=True,digest=digest)
                break
    except (OSError,ValueError,TypeError,AttributeError):
        pass
    return value


def collect(home):
    dependencies = load('dependency-lock')
    try:
        inventory = dependencies.runtime_inventory()
        reviewed = json.loads((ROOT/'voice/reviewed-stack.json').read_text())['packages']
        mismatches = {name:{'expected':version,'actual':inventory['packages'].get(name)}
                      for name,version in reviewed.items() if inventory['packages'].get(name)!=version}
        dependencies_result = {'status':'matches reviewed pins' if not mismatches else 'review required',
                               'inventory':inventory,'reviewed_mismatches':mismatches,
                               'yt_dlp_present':'yt-dlp' in inventory['packages']}
    except (OSError,RuntimeError,ValueError,KeyError,TypeError):
        dependencies_result = {'status':'capture unavailable; run with OVOS Python 3.11'}
    try:
        startup = load('startup_settings').inspect(home)
        startup['status'] = 'read-only login preference; successful next login not verified'
    except (OSError,RuntimeError,ValueError,KeyError,TypeError,configparser.Error,subprocess.SubprocessError):
        startup = {'status':'login settings need review; no changes made'}
    return {'schema_version':1,'status':'READ-ONLY EVIDENCE; not release acceptance',
            'dependencies':dependencies_result,'isolation':load('core-isolation-preflight').collect(),
            'settings':settings(home),'qwen_identity':model_identity(home),'startup':startup,
            'live_voice_verified':False,'external_egress_tested':False,
            'model_file_hashes_verified':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    output = args.output or Path.home()/'Downloads/jarvis-v4-laptop-check.json'
    load('dependency-lock').private_write(output,json.dumps(collect(Path.home()),indent=2)+'\n')
    print('Saved jarvis-v4-laptop-check.json. No installation, restart or external request performed.')


if __name__ == '__main__':
    try:
        main()
    except (OSError,ValueError):
        raise SystemExit('Could not save the private report. Choose a new output filename in an existing directory.')
