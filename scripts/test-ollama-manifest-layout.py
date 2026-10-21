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


# A fresh Ollama installation can update account membership while the desktop
# still has the old supplementary groups. Refresh only the model-copy child.
import errno
import grp
import pwd
import shlex
import subprocess
from types import SimpleNamespace
from contextlib import ExitStack

with tempfile.TemporaryDirectory() as folder:
    source, home, raw, digest, weight = fixture(Path(folder))
    account = SimpleNamespace(pw_name="fixture-user", pw_dir=str(home))
    group = SimpleNamespace(gr_gid=987654, gr_mem=["fixture-user"])
    denied = PermissionError(errno.EACCES, "fixture denial", str(source / weight))

    def membership(active=(), approved=True, account_home=None):
        stack = ExitStack()
        stack.enter_context(patch.object(pwd, "getpwuid", return_value=SimpleNamespace(
            pw_name=account.pw_name, pw_dir=str(account_home or home))))
        stack.enter_context(patch.object(grp, "getgrnam", return_value=SimpleNamespace(
            gr_gid=group.gr_gid, gr_mem=group.gr_mem if approved else [])))
        stack.enter_context(patch.object(model.os, "getgroups", return_value=list(active)))
        stack.enter_context(patch.object(model, "source_stores", return_value=[source]))
        return stack

    with membership():
        assert model._stale_model_group(home, denied) == group.gr_gid
        for path in (Path(folder) / "unrelated", model.private_root(home) / "models"):
            assert model._stale_model_group(home, PermissionError(
                errno.EACCES, "fixture denial", str(path))) is None
        assert model._stale_model_group(home, PermissionError()) is None
    with membership(approved=False):
        assert model._stale_model_group(home, denied) is None
    with membership(active=[group.gr_gid]):
        assert model._stale_model_group(home, denied) is None
    with membership(account_home=Path(folder) / "other-home"):
        assert model._stale_model_group(home, denied) is None
    with membership(), patch.object(grp, "getgrnam", side_effect=KeyError("ollama")):
        assert model._stale_model_group(home, denied) is None

    original_prepare = model._prepare_models
    parent_calls = []
    child_calls = []
    identity_before = (os.getuid(), os.getgid())

    def parent_prepare(selected_home, report=print):
        parent_calls.append(selected_home)
        if len(parent_calls) == 1:
            raise denied
        # Must verify the existing private copy without the general endpoint.
        with patch.object(model, "inventory_digest",
                          side_effect=AssertionError("General endpoint queried after copy")):
            return original_prepare(selected_home, report)

    def copy_child(command, *, stdin, check):
        child_calls.append(command)
        assert command[:3] == ["/usr/bin/sg", "ollama", "-c"]
        assert stdin is subprocess.DEVNULL and check is True
        argv = shlex.split(command[3])
        assert argv[0] == "exec"
        assert argv[2:4] == ["-I", "-c"]
        assert argv[-2:] == [str(Path(model.__file__).resolve().parent), str(home)]
        compile(argv[4], "<model-group-bootstrap>", "exec")
        assert "raise RuntimeError" in argv[4] and "assert " not in argv[4]
        original_prepare(home, lambda _: None)
        return subprocess.CompletedProcess(command, 0)

    with membership(), patch.object(model, "inventory_digest", return_value=digest), \
         patch.object(model, "verify_executable", return_value="/usr/bin/newgrp") as verified, \
         patch.object(model, "_prepare_models", side_effect=parent_prepare), \
         patch.object(model.subprocess, "run", side_effect=copy_child):
        model.prepare_models(home, lambda _: None)
    verified.assert_called_once_with("/usr/bin/sg")
    assert len(parent_calls) == 2 and len(child_calls) == 1
    copied = model.private_root(home) / "models"
    assert (copied / model.MANIFEST).read_bytes() == raw
    assert (copied / weight).read_bytes() == (source / weight).read_bytes()
    assert (copied / weight).stat().st_ino != (source / weight).stat().st_ino
    assert (copied / weight).stat().st_mode & 0o077 == 0
    assert (os.getuid(), os.getgid()) == identity_before
    model.remove_private_model(home)

    with membership(), patch.object(model, "_prepare_models", side_effect=denied), \
         patch.object(model.subprocess, "run",
                      side_effect=subprocess.CalledProcessError(1, ["sg"])) as child:
        try:
            model.prepare_models(home, lambda _: None)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError("Failed group copy was accepted")
        assert child.call_count == 1

    with membership(), patch.object(model, "_prepare_models", side_effect=denied), \
         patch.object(model.subprocess, "run",
                      return_value=subprocess.CompletedProcess(["sg"], 0)) as child:
        rejected(model.prepare_models, home, lambda _: None)
        assert child.call_count == 1 and not copied.exists()

    with membership(approved=False), \
         patch.object(model, "_prepare_models", side_effect=denied), \
         patch.object(model.subprocess, "run",
                      side_effect=AssertionError("Unapproved group was attempted")):
        rejected(model.prepare_models, home, lambda _: None)

print("PASS: stale approved model-group handoff, private-copy verification, unchanged parent identity and fail-closed refusals")

