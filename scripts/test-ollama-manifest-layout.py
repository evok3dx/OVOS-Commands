#!/usr/bin/env python3
"""Verify legacy and current Ollama model copies without a live daemon."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import private_ollama as model

if os.getuid() == 0:
    raise SystemExit("Run as a normal user, without sudo.")


def rejected(function, *args):
    try:
        function(*args)
    except (ValueError, RuntimeError, OSError):
        return
    raise AssertionError("Invalid model data was accepted")


def fixture(root, current=True, legacy=True):
    source = root / "source"
    (source / "blobs").mkdir(parents=True)
    weights = b"reviewed model weight fixture"
    weight_digest = hashlib.sha256(weights).hexdigest()
    weight_name = Path("blobs") / ("sha256-" + weight_digest)
    (source / weight_name).write_bytes(weights)
    data = {"schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {"digest": "sha256:" + weight_digest, "size": len(weights)},
            "layers": []}
    raw = json.dumps(data, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    manifest_blob = source / "blobs" / ("sha256-" + digest)
    if current:
        manifest_blob.write_bytes(raw)
        # This is Ollama's link, never a copied/accepted private-store symlink.
        v2 = source / "manifests-v2/ollama.com/library/qwen3/4b-instruct-2507-q4_K_M"
        v2.parent.mkdir(parents=True)
        v2.symlink_to(manifest_blob)
    if legacy:
        named = source / model.MANIFEST
        named.parent.mkdir(parents=True)
        if current:
            anchor = dict(data, layers=[{
                "mediaType": data["mediaType"],
                "digest": "sha256:" + digest, "size": len(raw)}])
            named.write_text(json.dumps(anchor))
        else:
            named.write_bytes(raw)
    home = root / "home"
    home.mkdir()
    return source, home, raw, digest, weight_name


def prepare(source, home, digest):
    with patch.object(model, "inventory_digest", return_value=digest), \
         patch.object(model, "source_stores", return_value=[source]):
        model.prepare_models(home, lambda _: None)


for current, legacy in ((False, True), (True, True), (True, False)):
    with tempfile.TemporaryDirectory() as folder:
        source, home, raw, digest, weight = fixture(Path(folder), current, legacy)
        original = {str(p.relative_to(source)): p.read_bytes()
                    for p in source.rglob("*") if p.is_file() and not p.is_symlink()}
        prepare(source, home, digest)
        copied = model.private_root(home) / "models"
        assert (copied / model.MANIFEST).read_bytes() == raw
        assert (copied / weight).read_bytes() == (source / weight).read_bytes()
        assert (copied / weight).stat().st_ino != (source / weight).stat().st_ino
        assert not any(p.is_symlink() for p in copied.rglob("*"))
        assert {str(p.relative_to(source)): p.read_bytes()
                for p in source.rglob("*") if p.is_file() and not p.is_symlink()} == original
        with patch.object(model, "inventory_digest", side_effect=AssertionError("General daemon queried")):
            model.prepare_models(home, lambda _: None)
        assert model.model_files(copied)[model.MANIFEST] == (digest, len(raw))
print("PASS: legacy, current-with-downgrade-anchor and current-only verified copies; private reuse")

for scenario in ("manifest-hash", "manifest-size", "manifest-link", "weight-hash",
                 "weight-size", "weight-link", "invalid-json", "manifest-list"):
    with tempfile.TemporaryDirectory() as folder:
        source, home, raw, digest, weight = fixture(Path(folder))
        manifest = source / "blobs" / ("sha256-" + digest)
        if scenario == "manifest-hash":
            manifest.write_bytes(b"tampered")
        elif scenario == "manifest-size":
            manifest.write_bytes(b"x" * 65537)
        elif scenario == "manifest-link":
            outside = Path(folder) / "outside"
            outside.write_bytes(raw)
            manifest.unlink()
            manifest.symlink_to(outside)
        elif scenario == "weight-hash":
            (source / weight).write_bytes(b"x" * (source / weight).stat().st_size)
        elif scenario == "weight-size":
            (source / weight).write_bytes(b"x")
        elif scenario == "weight-link":
            outside = Path(folder) / "outside"
            outside.write_bytes((source / weight).read_bytes())
            (source / weight).unlink()
            (source / weight).symlink_to(outside)
        elif scenario in ("invalid-json", "manifest-list"):
            manifest.unlink()
            raw = (b"not JSON" if scenario == "invalid-json" else
                   json.dumps({"mediaType": "application/vnd.ollama.manifest.list.v2+json",
                               "manifests": []}).encode())
            digest = hashlib.sha256(raw).hexdigest()
            (source / "blobs" / ("sha256-" + digest)).write_bytes(raw)
        rejected(prepare, source, home, digest)
        assert not (model.private_root(home) / "models").exists(), scenario
print("PASS: malformed, oversized, corrupt and symlinked data cannot commit a private store")

with tempfile.TemporaryDirectory() as folder:
    source, home, raw, digest, weight = fixture(Path(folder))
    for bad in ("../outside", "sha256:" + digest, "a" * 63, 42):
        rejected(model.model_files, source, bad)
    # No fallback to valid legacy bytes when a corrupt current blob is present.
    (source / model.MANIFEST).write_bytes(raw)
    (source / "blobs" / ("sha256-" + digest)).write_bytes(b"corrupt")
    rejected(prepare, source, home, digest)
    # A blob removed/changed during the copy must not commit a private store.
    (source / "blobs" / ("sha256-" + digest)).write_bytes(raw)
    original = model.model_files
    def changed_manifest(store, expected=None):
        files = original(store, expected)
        if expected is not None:
            (store / "blobs" / ("sha256-" + expected)).write_bytes(b"x" * len(raw))
        return files
    with patch.object(model, "model_files", side_effect=changed_manifest):
        rejected(prepare, source, home, digest)
    assert not (model.private_root(home) / "models").exists()
print("PASS: invalid identities, current-blob corruption and copy-time changes fail closed")
