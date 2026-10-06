#!/usr/bin/env python3
"""Read fixed, bounded result rows from the existing local voice bus."""
import json
import os
from pathlib import Path
import importlib.util
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from privacy_logging import quiet_reader


def main():
    if os.getuid() == 0:
        raise RuntimeError('Use the ordinary desktop user')
    output = quiet_reader()
    from ovos_bus_client import MessageBusClient, Message
    bus = MessageBusClient(host='127.0.0.1', port=8181, route='/core', ssl=False)
    bus.run_in_thread()
    try:
        if not bus.connected_event.wait(2):
            raise RuntimeError('Activity is unavailable while voice is stopped')
        reply = bus.wait_for_response(Message('jarvis.activity.snapshot'),
                                      'jarvis.activity.snapshot.response', timeout=2)
        if reply is None:
            raise RuntimeError('Activity is unavailable')
        spec = importlib.util.spec_from_file_location('jarvis_activity_reader',
                Path(__file__).resolve().parents[1] / 'ovos_skill_jarvis_dispatcher/activity.py')
        activity = importlib.util.module_from_spec(spec);spec.loader.exec_module(activity)
        activity.display_rows(reply.data)
        # Never relay extra fields supplied by another local bus client.
        data = json.dumps({'schema_version': 1, 'rows': [
            {key: row[key] for key in ('action', 'integration', 'success', 'time')}
            for row in reply.data['rows']]})
        if len(data.encode()) > 16384:
            raise ValueError('Activity response exceeds its limit')
        os.write(output, ('JARVIS_ACTIVITY_SNAPSHOT=' + data + '\n').encode())
    finally:
        try:bus.close()
        finally:os.close(output)


if __name__ == '__main__':
    main()
