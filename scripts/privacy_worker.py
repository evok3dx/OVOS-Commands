#!/usr/bin/env python3
"""Start only a fixed OVOS console entry point with private logging installed."""
import argparse
import os
from pathlib import Path
import runpy
import sys

LAUNCHERS = {'core': 'ovos-core', 'listener': 'ovos-dinkum-listener',
             'audio': 'ovos-audio', 'bus': 'ovos-messagebus'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=LAUNCHERS)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from privacy_logging import bootstrap, attach
    bootstrap(args.component)
    launcher = Path(sys.prefix) / 'bin' / LAUNCHERS[args.component]
    if not launcher.is_file() or launcher.is_symlink() or launcher.stat().st_uid != os.getuid():
        raise RuntimeError('Managed console launcher needs review')
    from ovos_bus_client import MessageBusClient
    bus = MessageBusClient(host='127.0.0.1', port=8181, route='/core', ssl=False)
    attach(bus)
    bus.run_in_thread()
    sys.argv = [str(launcher)]
    try:
        runpy.run_path(str(launcher), run_name='__main__')
    finally:
        bus.close()


if __name__ == '__main__':
    main()
