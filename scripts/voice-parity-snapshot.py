#!/usr/bin/env python3
"""Collect a small, private two-host OVOS comparison without raw settings."""

import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import re
import subprocess


PACKAGES = (
    "ovos-core", "ovos-workshop", "ovos-adapt-parser", "ovos-spec-tools",
    "ovos-plugin-manager", "ovos-config", "ovos-bus-client",
    "ovos-messagebus", "ovos-dinkum-listener", "ovos-audio",
    "ovos-microphone-plugin-alsa", "ovos-microphone-plugin-sounddevice",
    "ovos-skill-date-time", "ovos-skill-volume", "ovos-skill-boot-finished",
    "ovos-skill-fallback-unknown", "ovos-common-query-pipeline-plugin",
    "ovos-ocp-pipeline-plugin", "ovos-skill-jarvis-dispatcher",
    "ovos-stt-plugin-fasterwhisper", "faster-whisper", "ctranslate2",
    "ovos-ww-plugin-openwakeword", "openwakeword", "ovos-ww-plugin-vosk",
    "ovos-vad-plugin-silero", "phoonnx", "scriptconv", "misaki",
    "onnxruntime", "numpy",
)
UNITS = ("ovos-messagebus.service", "ovos-core.service",
         "ovos-listener.service", "ovos-audio.service", "ovos-phal.service")
LAUNCHERS = ("ovos-core", "ovos-audio", "ovos-dinkum-listener",
             "ovos-listen", "ovos-say-to", "ovos-speak")
NAME = re.compile(r"[A-Za-z0-9_.-]{1,90}\Z")


def mapping(value):
    return value if isinstance(value, dict) else {}


def safe_name(value):
    return value if isinstance(value, str) and NAME.fullmatch(value) else None


def setting(value):
    return value if type(value) in (bool, int, float) else None


def config():
    # Use the installed OVOS package to include its defaults and overrides.
    # Never serialise the returned object: it may contain credentials.
    from ovos_config import Configuration
    return Configuration()


def service_state(unit):
    result = subprocess.run(("systemctl", "--user", "is-active", unit),
                            capture_output=True, text=True, timeout=5)
    state = result.stdout.strip()
    return state if state in {"active", "inactive", "activating", "failed"} else "other"


def launcher_state(path, venv):
    if not path.is_file():
        return "missing"
    with path.open("rb") as handle:
        line = handle.readline(512)
    if not line.startswith(b"#!"):
        return "invalid-or-not-script"
    interpreter = line[2:].decode("utf-8", "replace").strip().split(" ", 1)[0]
    if interpreter.startswith(str(venv / "bin") + "/"):
        return "final-venv"
    if "/stage." in interpreter and "/ovos-venv/bin/" in interpreter:
        return "stale-stage"
    return "other"


def collect(label):
    home = Path.home()
    venv = home / ".venvs/ovos"
    conf = config()
    stt = mapping(conf.get("stt"))
    stt_name = safe_name(stt.get("module"))
    stt_options = mapping(stt.get(stt_name))
    tts = mapping(conf.get("tts"))
    tts_name = safe_name(tts.get("module"))
    tts_options = mapping(tts.get(tts_name))
    listener = mapping(conf.get("listener"))
    microphone = mapping(listener.get("microphone"))
    microphone_name = safe_name(microphone.get("module"))
    microphone_options = mapping(microphone.get(microphone_name))
    hotword = mapping(mapping(conf.get("hotwords")).get("hey_jarvis"))
    models = hotword.get("models")
    models = models if isinstance(models, list) else []
    pipeline = mapping(conf.get("intents")).get("pipeline")
    pipeline = pipeline if isinstance(pipeline, list) else []
    versions = {}
    for package in PACKAGES:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    launchers = {name: launcher_state(venv / "bin" / name, venv)
                 for name in LAUNCHERS}
    return {
        "label": label,
        "packages": versions,
        "services": {name: service_state(name) for name in UNITS},
        "launchers": launchers,
        "voice": {
            "listener": {
                key: setting(listener.get(key)) for key in
                ("instant_listen", "fake_barge_in", "barge_in_delay",
                 "barge_in_volume", "vad_pre_wake_enabled")
            },
            "microphone": {
                "module": microphone_name,
                "fallback_module": safe_name(
                    microphone_options.get("fallback_module")
                ),
            },
            "vad_module": safe_name(mapping(listener.get("VAD")).get("module")),
            "wake": {
                "module": safe_name(hotword.get("module")),
                "listen": setting(hotword.get("listen")),
                "threshold": setting(hotword.get("threshold")),
                "framework": safe_name(hotword.get("inference_framework")),
                "explicit_model_count": len(models),
                "explicit_onnx": any(str(m).endswith(".onnx") for m in models),
                "explicit_jarvis": any("hey_jarvis" in str(m) for m in models),
            },
            "stt": {
                "module": stt_name,
                "model": safe_name(stt_options.get("model")),
                "compute_type": safe_name(stt_options.get("compute_type")),
                "cpu_threads": setting(stt_options.get("cpu_threads")),
                "initial_prompt_configured": bool(stt_options.get("initial_prompt")),
            },
            "tts": {
                "module": tts_name,
                "bella_voice": tts_options.get("voice") == "kokoro/af_bella",
            },
            "listen_sound_configured": bool(mapping(conf.get("sounds")).get("start_listening")),
            "pipeline": [safe_name(s) or "[unusual stage]" for s in pipeline],
            "persona_fallback": setting(mapping(mapping(conf.get("intents")).get("persona")).get("handle_fallback")),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", choices=("reference", "laptop"), required=True)
    args = parser.parse_args()
    result = collect(args.label)
    output = Path.home() / "Downloads" / f"jarvis-voice-parity-{args.label}.json"
    output.parent.mkdir(exist_ok=True)
    # Refuse to replace a prior snapshot or follow a symlink.
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"Saved {output}. No raw configuration, paths, private phrases or keys included.")


if __name__ == "__main__":
    main()
