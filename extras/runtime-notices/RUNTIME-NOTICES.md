# Jarvis V4 test runtime notices

This separate runtime contains the exact 296-wheel closure recorded in
`voice/runtime-wheels-linux-x86_64-py311.artifacts.json`. Every wheel retains its
original metadata and bundled notices. The accompanying
`third-party-licenses.json` inventories those notices; it is not a legal
certification. Jarvis's own code remains under its repository licence.

## eSpeak NG

`espeakng-loader==0.2.4` contains eSpeak NG 1.52.0 shared libraries. The wheel
does not identify a separate COPYING/NOTICE or wrapper licence. The supplied
`espeak-ng-COPYING` is the unmodified upstream GNU GPL version 3 text, blob
`94a9ed024d3859793618152ea559a168bbcbb5e2`.

- [eSpeak NG source](https://github.com/espeak-ng/espeak-ng/tree/685480238072018edfc0e4f3d85e131c278c2ccf)
- [loader source and build recipe](https://github.com/thewh1teagle/espeakng-loader)
- [loader v1.52 submodule mapping](https://github.com/thewh1teagle/espeakng-loader/tree/e5e9200dc3fd894b7415942c2602fc31526d60fc)

The loader's v1.52 reference points to the eSpeak source above, but its wrapper
version differs from PyPI 0.2.4. Exact correspondence for that PyPI binary and
the wrapper's licence still require upstream confirmation before broader
redistribution. These source pointers must not be described as verified complete
corresponding source for the wheel.

## PyAV and its native libraries

`av==18.1.0` includes native FFmpeg and other libraries in addition to its
BSD-licensed Python binding. Retain their wheel notices and review the individual
native licences when preparing broader distribution. Do not apply the Python
binding's BSD licence to every native library.

- [PyAV 18.1.0 source](https://github.com/PyAV-Org/PyAV/tree/v18.1.0)
- [vendor source URLs, checksums and build recipes](https://github.com/PyAV-Org/pyav-ffmpeg/tree/a71bf9279f7a4659154b68ba6783e89be460bcd5)

This laptop test release keeps the reviewed versions and hashes unchanged.
Production signing, broader packaging and final redistribution review remain
separate from the owner's current laptop testing approval.
