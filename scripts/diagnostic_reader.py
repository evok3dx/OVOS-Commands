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
            reply = bus.wait_for_response(Message(topic), topic + '.response', timeout=2)
            return [] if reply is None else display(reply.data)
        with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
            rows = [row for batch in pool.map(fetch, ROLES) for row in batch]
        if not mode()['enabled']:
            return 'Diagnostics finished. No logs are being kept.'
        return '\n'.join(rows)[:20000] or 'Diagnostics enabled. No technical events captured yet.'
    finally:
        bus.close()


if __name__ == '__main__':
    output = quiet_reader()
    try:
        os.write(output, (read() + '\n').encode())
    finally:
        os.close(output)
