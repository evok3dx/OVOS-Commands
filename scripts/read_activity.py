#!/usr/bin/env python3
"""Read fixed, bounded result rows from the existing local voice bus."""
import json
import os
from ovos_bus_client import MessageBusClient, Message


def main():
    if os.getuid() == 0:
        raise RuntimeError('Use the ordinary desktop user')
    bus = MessageBusClient(host='127.0.0.1', port=8181, route='/core', ssl=False)
    bus.run_in_thread()
    try:
        if not bus.connected_event.wait(2):
            raise RuntimeError('Activity is unavailable while voice is stopped')
        reply = bus.wait_for_response(Message('jarvis.activity.snapshot'),
                                      'jarvis.activity.snapshot.response', timeout=2)
        if reply is None:
            raise RuntimeError('Activity is unavailable')
        data = json.dumps(reply.data)
        if len(data.encode()) > 16384:
            raise ValueError('Activity response exceeds its limit')
        print(data)
    finally:
        bus.close()


if __name__ == '__main__':
    main()
