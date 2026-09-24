"""In-process bridge between the Media skill and its routing pipeline."""
import weakref


_SKILL = None


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
