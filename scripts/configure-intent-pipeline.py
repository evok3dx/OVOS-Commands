#!/usr/bin/env python3
"""Install Jarvis's reviewed OVOS intent pipeline using available plugins."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import tempfile
from pathlib import Path


LEGACY_STAGE_PLUGINS = {
    "converse": "ovos-converse-pipeline-plugin",
    "common_qa": "ovos-common-query-pipeline-plugin",
    "fallback_high": "ovos-fallback-pipeline-plugin",
    "fallback_medium": "ovos-fallback-pipeline-plugin",
    "fallback_low": "ovos-fallback-pipeline-plugin",
    "stop_high": "ovos-stop-pipeline-plugin",
    "stop_medium": "ovos-stop-pipeline-plugin",
    "stop_low": "ovos-stop-pipeline-plugin",
    "adapt_high": "ovos-adapt-pipeline-plugin",
    "adapt_medium": "ovos-adapt-pipeline-plugin",
    "adapt_low": "ovos-adapt-pipeline-plugin",
    "padatious_high": "ovos-padatious-pipeline-plugin",
    "padatious_medium": "ovos-padatious-pipeline-plugin",
    "padatious_low": "ovos-padatious-pipeline-plugin",
    "padacioso_high": "ovos-padacioso-pipeline-plugin",
    "padacioso_medium": "ovos-padacioso-pipeline-plugin",
    "padacioso_low": "ovos-padacioso-pipeline-plugin",
    "ocp_high": "ovos-ocp-pipeline-plugin",
    "ocp_medium": "ovos-ocp-pipeline-plugin",
    "ocp_low": "ovos-ocp-pipeline-plugin",
    "ocp_legacy": "ovos-ocp-pipeline-plugin",
}
CONFIDENCE_SUFFIXES = ("-high", "-medium", "-low", "-legacy")


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"configuration root is not an object: {path}")
    return value


def atomic_write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".new", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(mode)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def pipeline_plugin(stage: str) -> str:
    if stage in LEGACY_STAGE_PLUGINS:
        return LEGACY_STAGE_PLUGINS[stage]
    for suffix in CONFIDENCE_SUFFIXES:
        if stage.endswith(suffix):
            return stage[: -len(suffix)]
    return stage


def filter_pipeline(
    pipeline: list[object], available_plugins: set[str]
) -> tuple[list[str], list[str]]:
    if not all(isinstance(stage, str) and stage for stage in pipeline):
        raise ValueError("OVOS intents.pipeline must contain non-empty strings")
    retained = []
    removed = []
    for stage in pipeline:
        plugin = pipeline_plugin(stage)
        if stage in available_plugins or plugin in available_plugins:
            retained.append(stage)
        else:
            removed.append(stage)
    if not retained:
        raise ValueError("no usable OVOS intent pipeline stages were detected")
    return retained, removed


def installed_pipeline_plugins() -> set[str]:
    try:
        entries = metadata.entry_points(group="opm.pipeline")
    except TypeError:  # Python/importlib-metadata compatibility
        entries = metadata.entry_points().select(group="opm.pipeline")
    return {entry.name for entry in entries}


def reviewed_pipeline(compatibility_path: Path) -> list[object]:
    compatibility = load_json(compatibility_path)
    ovos = compatibility.get("ovos")
    if not isinstance(ovos, dict):
        raise ValueError("compatibility metadata has no OVOS section")
    pipeline = ovos.get("intent_pipeline")
    if not isinstance(pipeline, list):
        raise ValueError("compatibility metadata has no reviewed intent pipeline")
    return pipeline


def merge_v3_pipeline(existing: list[object]) -> list[str]:
    """Add the three local stages without changing unrelated host routing."""
    if not isinstance(existing, list) or not all(isinstance(s, str) and s for s in existing):
        raise ValueError("OVOS intents.pipeline must be a list of stage names")
    stages = [stage for stage in existing if stage not in (
        "jarvis-media-pipeline", "jarvis-qwen-pipeline", "jarvis-qwen-chat-pipeline")]
    medium = "ovos-fallback-pipeline-plugin-medium"
    low = "ovos-fallback-pipeline-plugin-low"
    if medium not in stages or low not in stages:
        raise ValueError("The reviewed medium and low fallback stages are missing")
    index = stages.index(medium)
    stages[index:index] = ["jarvis-media-pipeline", "jarvis-qwen-pipeline"]
    stages.insert(stages.index(low), "jarvis-qwen-chat-pipeline")
    return stages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path,
        default=Path.home() / ".config/mycroft/mycroft.conf",
    )
    parser.add_argument(
        "--compatibility", type=Path,
        default=Path(__file__).resolve().parents[1] / "compatibility.json",
        help="Compatibility metadata containing the reviewed pipeline",
    )
    parser.add_argument(
        "--available-plugin", action="append", default=None,
        help="Use an explicit available plugin ID (repeatable)",
    )
    parser.add_argument("--merge-v3", action="store_true",
                        help="add reviewed local Media and Qwen stages while retaining existing stages")
    args = parser.parse_args()

    available = (
        set(args.available_plugin)
        if args.available_plugin is not None else installed_pipeline_plugins()
    )
    local = load_json(args.config)
    intents = local.setdefault("intents", {})
    if not isinstance(intents, dict):
        raise ValueError("local OVOS intents setting is not an object")
    baseline = (intents.get("pipeline", reviewed_pipeline(args.compatibility))
                if args.merge_v3 else reviewed_pipeline(args.compatibility))
    if args.merge_v3:
        baseline = merge_v3_pipeline(baseline)
        required = {"jarvis-media-pipeline", "jarvis-qwen-pipeline",
                    "jarvis-qwen-chat-pipeline"}
        missing = required - available
        if missing:
            raise ValueError("Required local pipeline entry points missing: " + ", ".join(sorted(missing)))
        persona = intents.setdefault("persona", {})
        if not isinstance(persona, dict) or persona.get("handle_fallback") is True:
            raise ValueError("An existing persona fallback setting needs manual review")
        persona["handle_fallback"] = False
    if args.merge_v3:
        # Existing private or machine-specific stages are the owner's policy.
        # A V3 update only adds its three verified local stages.
        retained, removed = baseline, []
    else:
        retained, removed = filter_pipeline(baseline, available)
    if intents.get("pipeline") == retained:
        print("OVOS intent pipeline already matches the reviewed Jarvis baseline.")
        return 0
    intents["pipeline"] = retained
    atomic_write(args.config, local)
    print("Configured the reviewed Jarvis intent pipeline.")
    if removed:
        print("Skipped unavailable reviewed stages: " + ", ".join(removed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
