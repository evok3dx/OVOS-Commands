#!/usr/bin/env python3
"""Read-only capability inventory. Never enables isolation or claims enforcement."""
import json
from pathlib import Path
import shutil
import subprocess

UNITS=('ovos-messagebus.service','ovos-core.service','ovos-listener.service',
       'ovos-audio.service','ovos-phal.service','ollama.service')

def inspect(unit, scope='user'):
    try:
        result=subprocess.run(['systemctl','--'+scope,'show',unit,'--no-pager',
                               '--property=LoadState,ActiveState,IPAddressDeny,IPAddressAllow,IPAccounting'],
                              capture_output=True,text=True,timeout=5)
    except (OSError,subprocess.SubprocessError): return {'service':unit,'scope':scope,'inspectable':False}
    properties=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    # Do not export ExecStart, environment, paths, machine names or raw addresses.
    deny=properties.get('IPAddressDeny','').split()
    return {'service':unit,'scope':scope,'inspectable':result.returncode==0 and 'LoadState' in properties,
            'loaded':properties.get('LoadState')=='loaded',
            'active':properties.get('ActiveState')=='active',
            'deny_rule_present':bool(properties.get('IPAddressDeny')),
            'deny_all_families_configured':('any' in deny or {'0.0.0.0/0','::/0'}.issubset(deny)),
            'allow_rule_present':bool(properties.get('IPAddressAllow')),
            'ip_accounting':properties.get('IPAccounting')=='yes'}

def capabilities():
    value={'cgroup_v2_visible':Path('/sys/fs/cgroup/cgroup.controllers').is_file(),
           'unprivileged_bpf_disabled':None,'effective_bpf_or_admin_capability':False,
           'basis':'read-only host indicators; unit-level enforcement not tested'}
    try:
        mode=Path('/proc/sys/kernel/unprivileged_bpf_disabled').read_text().strip()
        if mode in {'0','1','2'}:value['unprivileged_bpf_disabled']=int(mode)
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('CapEff:'):
                mask=int(line.split(':',1)[1].strip(),16)
                value['effective_bpf_or_admin_capability']=any(mask & (1<<bit) for bit in (12,21,39))
    except (OSError,ValueError):pass
    return value

def collect():
    return {'schema_version':1,'status':'NOT VERIFIED: inventory only',
          'systemd_tool_available':bool(shutil.which('systemctl')),
          'kernel_capability_indicators':capabilities(),
          'services':[inspect(unit) for unit in UNITS]+[inspect('ollama.service','system')],
          'next_gate':'Prove IPv4/IPv6/UDP egress denial in actual service cgroups and working loopback/desktop handoffs; separate online skills first.'}

if __name__=='__main__':
    print(json.dumps(collect(),indent=2))
