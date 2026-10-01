"""In-process bridge between the Media skill and its routing pipeline."""
import weakref


_SKILL = None
_REMOTE_ENABLED = False


def enable_remote(enabled):
    """In-memory isolation policy, derived from the owner's original blacklist."""
    global _REMOTE_ENABLED
    _REMOTE_ENABLED = enabled is True


def remote_enabled():
    return _REMOTE_ENABLED


def register(skill):
    global _SKILL
    _SKILL = weakref.ref(skill)


def unregister(skill):
    global _SKILL
    current = get_skill()
    if current is skill:
        _SKILL = None


def get_skill():
    return _SKILL() if _SKILL is not None else None
