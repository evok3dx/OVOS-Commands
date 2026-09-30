#!/usr/bin/env python3
"""Select and load the installed, official Hey Jarvis ONNX wake model."""

import sys
from contextlib import redirect_stdout
from pathlib import Path

from openwakeword import Model, get_pretrained_model_paths


def reviewed_onnx_model() -> Path:
    # openWakeWord defaults to TFLite. Its ONNX paths must be requested
    # explicitly to preserve the reviewed engine across dependency repairs.
    paths = get_pretrained_model_paths(inference_framework="onnx") or []
    models = [Path(path) for path in paths
              if Path(path).name.startswith("hey_jarvis_")
              and Path(path).suffix == ".onnx" and Path(path).is_file()]
    if len(models) != 1:
        raise RuntimeError("Expected exactly one installed Hey Jarvis ONNX model")
    with redirect_stdout(sys.stderr):
        loaded = Model(wakeword_models=[str(models[0])],
                       inference_framework="onnx")
    if not loaded.models:
        raise RuntimeError("Installed Hey Jarvis ONNX model cannot load")
    return models[0]


if __name__ == "__main__":
    try:
        print(reviewed_onnx_model())
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
