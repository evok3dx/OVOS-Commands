#!/usr/bin/env python3
"""Read only bounded, content-free diagnostic rows from the local bus."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from privacy_logging import ROLES, display, mode, quiet_reader


def read():
    if not mode()['enabled']:
        return 'No logs. Enable Diagnostics for 5 minutes in General.'
    from ovos_bus_client import MessageBusClient, Message
    bus = MessageBusClient(host='127.0.0.1', port=8181, route='/core', ssl=False)
    bus.run_in_thread()
    try:
        if not bus.connected_event.wait(2):
            return 'Diagnostics unavailable while the voice bus is stopped.'
        def fetch(role):
            topic = 'jarvis.diagnostics.' + role
            try:
                reply = bus.wait_for_response(Message(topic), topic + '.response', timeout=2)
                if reply is None:
                    return role + ': no diagnostic response (stopped, disabled or unavailable).', []
                if not isinstance(reply.data, dict) or reply.data.get('component') != role:
                    raise ValueError('Wrong diagnostic component')
                rows = display(reply.data)
                return role + ': diagnostic collector responding.', rows or [role + ': no captured warnings or reviewed events.']
            except Exception:
                return role + ': diagnostic response unavailable or invalid.', []
        # Ordinary deployments load online skills in core, so they have no
        # standalone collector. Do not describe those absent roles as failed.
        from isolation_services import active
        try:
            roles = ROLES if active() else tuple(role for role in ROLES if role not in ('weather', 'media'))
        except (ValueError, OSError, RuntimeError):
            return 'Diagnostic component mapping unavailable. Review isolation status in Maintenance.'
        with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
            batches = list(pool.map(fetch, roles))
        if not mode()['enabled']:
            return 'Diagnostics finished. No logs are being kept.'
        # Collector summaries always appear before bounded event detail, so a
        # noisy core cannot hide a missing listener or online helper.
        rows = [status for status, _ in batches]
        rows += [row for _, events in batches for row in events[:32]]
        return '\n'.join(rows)[:20000]
    finally:
        bus.close()


if __name__ == '__main__':
    output = quiet_reader()
    try:
        try:
            result = read()
        except Exception:
            result = 'Diagnostics unavailable. Check service status in Dashboard.'
        os.write(output, (result + '\n').encode())
    finally:
        os.close(output)
