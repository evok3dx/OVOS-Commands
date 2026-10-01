#!/usr/bin/env python3
"""Explicit fixed socket tests inside V4 workers over the existing local bus.

No start/restart, microphone change, policy installation or new listening port.
This is separate from the immutable supplied temporary-policy v2 report.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import threading
import time
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from isolation_services import active,regular
from isolation_worker import worker_identity
from model_endpoint import model_port

EVENT='jarvis.v4.isolation.probe'
COMPONENTS=('core','listener','audio')
EXTERNAL=('ipv4_tcp','ipv6_tcp','ipv4_dns_udp','ipv6_dns_udp')
LOCAL=('messagebus_loopback','ollama_loopback')
OUTCOMES={'connected','timeout','permission_denied','unreachable','refused','unavailable'}


def network_test(family,host,port,dns=False):
    kind=socket.SOCK_DGRAM if dns else socket.SOCK_STREAM
    try:
        with socket.socket(family,kind) as connection:
            connection.settimeout(1.5);connection.connect((host,port))
            if dns:
                # Fixed example.org A query. Never sends utterances or configuration.
                query=b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03org\x00\x00\x01\x00\x01'
                connection.send(query)
                reply=connection.recv(4096)
                if len(reply)<12 or reply[:2]!=query[:2] or not reply[2]&0x80:
                    return {'reachable':False,'outcome':'unavailable'}
        return {'reachable':True,'outcome':'connected'}
    except TimeoutError:outcome='timeout'
    except PermissionError:outcome='permission_denied'
    except ConnectionRefusedError:outcome='refused'
    except OSError:outcome='unreachable'
    return {'reachable':False,'outcome':outcome}


def tests():
    return {'ipv4_tcp':network_test(socket.AF_INET,'1.1.1.1',443),
            'ipv6_tcp':network_test(socket.AF_INET6,'2606:4700:4700::1111',443),
            'ipv4_dns_udp':network_test(socket.AF_INET,'1.1.1.1',53,True),
            'ipv6_dns_udp':network_test(socket.AF_INET6,'2606:4700:4700::1111',53,True),
            'messagebus_loopback':network_test(socket.AF_INET,'127.0.0.1',8181),
            'ollama_loopback':network_test(socket.AF_INET,'127.0.0.1',model_port())}


def assessment(before,worker,after):
    identity=worker.get('status')=='completed' and worker.get('unit_context_verified') is True and worker.get('desktop_user_identity_verified') is True
    checks=worker.get('tests',{})
    compared={key:before.get(key,{}).get('reachable') is True and after.get(key,{}).get('reachable') is True for key in EXTERNAL}
    denied={key:identity and compared[key] and checks.get(key,{}).get('reachable') is False
            and checks.get(key,{}).get('outcome') in {'permission_denied','timeout'} for key in EXTERNAL}
    local=identity and all(round.get(key,{}).get('reachable') is True for round in (before,checks,after) for key in LOCAL)
    passed=all(denied.values()) and local
    return {'status':'ACTUAL WORKER SOCKET COMPARISON PASSED' if passed else 'INCONCLUSIVE OR NOT ENFORCED',
            'tested_paths':{key:'blocked' if denied[key] else 'inconclusive_or_not_enforced' for key in EXTERNAL},
            'all_external_paths_compared':all(compared.values()),'all_external_paths_denied':all(denied.values()),
            'required_loopback_preserved':local}


def ticket_directory():
    root=Path.home()/'.local/state/jarvis/isolation/probes'
    if any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('Probe staging must be regular')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if root.stat().st_uid!=os.getuid() or root.stat().st_mode & 0o077:raise ValueError('Probe staging must be private')
    return root


def claim(token,component,now=None):
    if component not in COMPONENTS or not isinstance(token,str) or not re.fullmatch('[a-f0-9]{32}',token):return False
    root=ticket_directory();path=root/(token+'.json');used=root/(token+'-'+component+'.used')
    try:
        value=json.loads(regular(path,private=True,limit=1024))
        timestamp=time.time() if now is None else now
        if (not isinstance(value,dict) or set(value)!={'expires','components'}
                or type(value['expires']) not in {int,float} or not math.isfinite(value['expires'])
                or not timestamp<value['expires']<=timestamp+60 or value['components']!=list(COMPONENTS)):
            return False
        from prepare_core_isolation import private_file
        private_file(used,'used\n')
        if not path.exists():
            used.unlink(missing_ok=True);return False
        return True
    except (OSError,ValueError):return False


def source_hash():
    return hashlib.sha256(Path(__file__).with_name('isolation_worker.py').read_bytes()).hexdigest()


def attach(component,uid,gid):
    if component not in COMPONENTS:return None
    from ovos_bus_client import MessageBusClient,Message
    bus=MessageBusClient(host='127.0.0.1',port=8181,ssl=False)
    loaded_source=source_hash()
    def handle(message):
        value=message.data
        if not isinstance(value,dict) or set(value)!={'token','test_network'} or value['test_network'] is not True:return
        if not claim(value['token'],component):return
        result={'component':component,'token':value['token'],'status':'worker_identity_unverified'}
        try:
            worker_identity(component,uid,gid)
            result.update(status='completed',unit_context_verified=True,desktop_user_identity_verified=True,
                          tests=tests(),worker_source_sha256=loaded_source)
        except (OSError,ValueError,RuntimeError):pass
        bus.emit(Message(EVENT+'.response',result))
    bus.on(EVENT,handle);bus.run_in_thread()
    return bus


def safe_worker(value,expected):
    if value.get('worker_source_sha256')!=expected:return {'status':'worker_source_unverified'}
    checks=value.get('tests',{})
    if not isinstance(checks,dict):return {'status':'worker_data_unverified'}
    clean={}
    for name in (*EXTERNAL,*LOCAL):
        result=checks.get(name)
        if not isinstance(result,dict) or type(result.get('reachable')) is not bool or result.get('outcome') not in OUTCOMES:
            return {'status':'worker_data_unverified'}
        clean[name]={'reachable':result['reachable'],'outcome':result['outcome']}
    return {'status':'completed' if value.get('status')=='completed' else 'worker_identity_unverified',
            'unit_context_verified':value.get('unit_context_verified') is True,
            'desktop_user_identity_verified':value.get('desktop_user_identity_verified') is True,'tests':clean}


def collect(timeout=25):
    if not active() or os.getuid()<=0 or os.getuid()!=os.geteuid() or os.getgid()!=os.getegid():
        raise ValueError('Activate reviewed candidate and run as the normal desktop user')
    if '/system.slice/jarvis-v4-' in Path('/proc/self/cgroup').read_text():
        raise ValueError('Run unrestricted controls outside worker cgroups')
    before=tests();expected=source_hash();root=ticket_directory();token=secrets.token_hex(16)
    ticket=root/(token+'.json');bus=None;results={};condition=threading.Condition()
    def receive(message):
        value=message.data
        if not isinstance(value,dict) or value.get('token')!=token or value.get('component') not in COMPONENTS:return
        clean=safe_worker(value,expected)
        with condition:
            results.setdefault(value['component'],clean);condition.notify_all()
    from prepare_core_isolation import private_file
    private_file(ticket,json.dumps({'expires':time.time()+45,'components':list(COMPONENTS)}))
    try:
        from ovos_bus_client import MessageBusClient,Message
        bus=MessageBusClient(host='127.0.0.1',port=8181,ssl=False)
        bus.on(EVENT+'.response',receive);bus.run_in_thread()
        if not bus.connected_event.wait(3):raise RuntimeError('Existing messagebus unavailable; no service was started')
        bus.emit(Message(EVENT,{'token':token,'test_network':True}))
        with condition:condition.wait_for(lambda:len(results)==len(COMPONENTS),timeout=timeout)
        after=tests()
        workers={name:{'result':results.get(name,{'status':'INCONCLUSIVE: stopped, muted or unavailable worker'}),
                       'assessment':assessment(before,results.get(name,{}),after)} for name in COMPONENTS}
        passed=all(value['assessment']['all_external_paths_denied'] and value['assessment']['required_loopback_preserved'] for value in workers.values())
        return {'schema_version':1,'collector_version':3,'collector_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'expected_worker_source_sha256':expected,'status':'ACTUAL WORKER SOCKET TESTS PASSED' if passed else 'INCONCLUSIVE OR NOT ENFORCED',
                'workers':workers,'controls':{'before':before,'after':after},'actual_core_listener_audio_socket_tests_passed':passed,
                'services_modified':False,'microphone_changed':False,'ollama_service_egress_verified':False,
                'application_layer_and_mediated_egress_verified':False,
                'claim':'Socket tests only. Voice, desktop, DNS/proxy mediation, Ollama and recovery remain gates.'}
    finally:
        try:
            if bus is not None:bus.close()
        finally:
            ticket.unlink(missing_ok=True)
            for name in COMPONENTS:(root/(token+'-'+name+'.used')).unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-network',action='store_true');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.test_network:parser.error('Explicit --test-network required for fixed public socket tests')
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():parser.error('Choose a new private output path')
    report=collect()
    from prepare_core_isolation import private_file
    private_file(args.output,json.dumps(report,indent=2)+'\n')
    print('Saved private actual-worker socket evidence; no services or microphone state changed.')


if __name__=='__main__':main()
