# OCP Stop compatibility

The reviewed `ovos-plugin-common-play 1.3.10a1` media player implements
`stop()` but not the `can_stop()` method required by the reviewed
`ovos-workshop 9.8.7a1` STOP-1 handshake. A spoken `Stop` therefore produces a
`NotImplementedError` in `ovos-audio` before the other stop subscribers finish.

`install.py` accepts only the exact reviewed upstream source (or this exact
patch), adds a state-based `can_stop()` method, compiles the result before
writing it atomically, and refuses unknown source. The main installer records
the original file in its transactional rollback snapshot.
