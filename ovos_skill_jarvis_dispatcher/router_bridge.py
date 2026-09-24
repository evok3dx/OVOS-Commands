"""Process-local link to the already initialised dispatcher; no new bus actions."""

import weakref

_dispatcher = None


def register_dispatcher(skill):
    global _dispatcher
    _dispatcher = weakref.ref(skill)


def unregister_dispatcher(skill):
    global _dispatcher
    if get_dispatcher() is skill:
        _dispatcher = None


def get_dispatcher():
    return _dispatcher() if _dispatcher else None
