#!/usr/bin/env python3
"""Read-only policy inspection and explicitly requested direct network checks."""
import argparse
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
from isolation_services import active
from model_endpoint import model_port
from private_reports import new_directory


def properties(part):
    result = subprocess.run(['/usr/bin/systemctl', '--system', '--no-pager', '--no-ask-password',
                             'show', f'jarvis-v4-{os.getuid()}-{part}.service',
                             '--property=LoadState,ActiveState,MainPID,User,NoNewPrivileges,IPAddressDeny,IPAddressAllow'],
                            capture_output=True, text=True, timeout=10, check=True)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def api(route, payload, timeout):
    connection = http.client.HTTPConnection('127.0.0.1', 11435, timeout=timeout)
    try:
        connection.request('POST', route, json.dumps(payload), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        data = response.read(1048577)
        if len(data) > 1048576:
            raise ValueError('Model response exceeds limit')
        return json.loads(data)
    finally:
        connection.close()


def outside_ipv4():
    try:
        with socket.create_connection(('1.1.1.1', 443), timeout=5):
            return True
    except OSError:
        return False


def policy_status():
    """Current native policy only; never imply actual egress was tested."""
    mapping = active()
    port = model_port()
    states = {part: properties(part) for part in ('core', 'listener', 'audio', 'ollama')}

    def restricted(value):
        denied = set(value.get('IPAddressDeny', '').split())
        allowed = set(value.get('IPAddressAllow', '').split())
        return (value.get('LoadState') == 'loaded'
                and value.get('User') == str(os.getuid())
                and value.get('NoNewPrivileges') == 'yes'
                and {'0.0.0.0/0', '::/0'} <= denied
                and allowed <= {'127.0.0.1/32', '::1/128'}
                and '127.0.0.1/32' in allowed)

    core = mapping and all(restricted(states[part]) for part in ('core', 'listener', 'audio'))
    model = port == 11435 and restricted(states['ollama'])
    absent = all(value.get('LoadState') == 'not-found' for value in states.values())
    summary = 'active' if core and model else 'off' if not mapping and absent and port != 11435 else 'attention'
    return {'summary': summary, 'core': bool(core), 'model': bool(model),
            'verification': 'Network tests have not been run in this view.'}


def model_checks():
    original = properties('ollama')
    if original.get('ActiveState') != 'active' or original.get('MainPID') in {None, '0'}:
        return {'status': 'INCONCLUSIVE: dedicated model is not running'}
    result = {}
    try:
        generation = api('/api/generate', {'model': 'qwen3:4b-instruct-2507-q4_K_M',
                         'prompt': 'Reply only OK.', 'stream': False,
                         'options': {'num_predict': 8}}, 120)
        result['local_generation'] = bool(generation.get('done') is True and generation.get('response'))
    except (OSError, ValueError, http.client.HTTPException):
        result['local_generation'] = 'INCONCLUSIVE'
    before = outside_ipv4()
    try:
        pull = api('/api/pull', {'model': '1.1.1.1/jarvis-egress-probe/nonexistent:diagnostic', 'stream': False}, 40)
        error = str(pull.get('error', ''))
        denied = ('dial tcp 1.1.1.1:443' in error
                  and any(word in error for word in ('i/o timeout', 'operation not permitted')))
    except (OSError, ValueError, http.client.HTTPException):
        denied = False
    after = outside_ipv4()
    latest = properties('ollama')
    same = (latest.get('ActiveState') == 'active'
            and latest.get('MainPID') == original['MainPID'])
    result['model_IPv4'] = {'status': 'PASS' if before and after and same and denied else 'INCONCLUSIVE',
                            'outside_before': before, 'outside_after': after,
                            'same_daemon': same, 'daemon_denied': denied}
    result['model_IPv6'] = {'status': 'NOT TESTED',
                          'reason': 'Model-name validation prevents the bracketed numeric IPv6 registry probe; policy inspection is not an actual daemon test.'}
    return result


def collect(network=False, model=False):
    result = {'schema_version': 1, 'isolation_mapping_active': active(),
              'selected_model_port': model_port(),
              'scope': 'Direct socket checks only. No fresh-install, login, mediated or inherited socket claim.',
              'services_modified': False, 'microphone_changed': False}
    for part in ('core', 'listener', 'audio', 'weather', 'media', 'ollama'):
        result[part] = properties(part)
    workers = None
    if result['isolation_mapping_active']:
        if network:
            from verify_core_isolation import collect as worker_checks
            try:
                workers = worker_checks()
                result['worker_tests'] = workers['status']
            except (OSError, RuntimeError, ValueError):
                result['worker_tests'] = 'INCONCLUSIVE: workers or controls unavailable'
        if model and result['selected_model_port'] == 11435:
            result.update(model_checks())
    else:
        result['worker_tests'] = 'NOT TESTED: isolation has not been activated'
    return result, workers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-network', action='store_true', help='Compare actual worker sockets with external controls')
    parser.add_argument('--test-model', action='store_true', help='Generate a fixed local reply and test dedicated daemon IPv4 denial')
    args = parser.parse_args()
    if os.getuid() == 0:
        parser.error('Run as the ordinary desktop user, without sudo')
    output = new_directory(Path.home() / 'Downloads', 'Jarvis-Isolation-Check')
    result, workers = collect(args.test_network, args.test_model)
    from prepare_core_isolation import private_file
    private_file(output / 'summary.json', json.dumps(result, indent=2) + '\n')
    if workers is not None:
        private_file(output / 'workers.json', json.dumps(workers, indent=2) + '\n')
    print('Isolation mapping: ' + ('active' if result['isolation_mapping_active'] else 'not activated'))
    print('Workers: ' + result.get('worker_tests', 'not tested'))
    if args.test_model:
        print('Local generation: ' + str(result.get('local_generation', 'not tested')))
        print('Private model IPv4: ' + result.get('model_IPv4', {}).get('status', 'not tested'))
        print('Private model IPv6: ' + result.get('model_IPv6', {}).get('status', 'not tested'))
    print('Report folder: ' + str(output))


if __name__ == '__main__':
    main()
