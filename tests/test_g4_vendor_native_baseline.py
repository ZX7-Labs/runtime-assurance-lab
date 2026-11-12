"""Offline adversarial tests for public native-vendor research boundaries."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import g4_vendor_native_baseline as native


def _tgz(member_name="aicr", data=b"TEST-ELF-BYTES", *, kind=tarfile.REGTYPE):
    file = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=file) as tar:
        entry = tarfile.TarInfo(member_name)
        entry.size = len(data) if kind == tarfile.REGTYPE else 0
        entry.type = kind
        tar.addfile(entry, io.BytesIO(data) if kind == tarfile.REGTYPE else None)
    return file.getvalue()


def test_pinned_bytes_match():
    data = b"immutable"
    assert native.checked_bytes(data, hashlib.sha256(data).hexdigest(), 50) == data


@pytest.mark.parametrize("raw", [b"", b"a" * 51, b"changed"])
def test_broken_release_rejected(raw):
    with pytest.raises(native.BaselineError):
        native.checked_bytes(raw, hashlib.sha256(b"immutable").hexdigest(), 50)


def test_signed_bundle_requires_independent_verifier(monkeypatch):
    def download(key):
        return _tgz("aicr" if key == "aicr" else "kubectl-aibom") if key != "aibom_provenance" else b"signed-metadata"
    monkeypatch.setattr(native, "download", download)
    monkeypatch.setattr(native.shutil, "which", lambda _: None)
    with pytest.raises(native.BaselineError, match="independent gh attestation verifier unavailable"):
        native.execute()


def test_binary_extraction_rejects_symlink(tmp_path):
    with pytest.raises(native.BaselineError, match="regular file"):
        native.extract_one_binary(_tgz(kind=tarfile.SYMTYPE), "aicr", tmp_path / "aicr")


@pytest.mark.parametrize("name", ["../aicr", "/tmp/aicr"])
def test_binary_extraction_rejects_unsafe_name(name, tmp_path):
    with pytest.raises(native.BaselineError, match="path or size"):
        native.extract_one_binary(_tgz(name), "aicr", tmp_path / "aicr")


def test_binary_extraction_missing_or_duplicate(tmp_path):
    with pytest.raises(native.BaselineError, match="exactly one"):
        native.extract_one_binary(_tgz("different"), "aicr", tmp_path / "aicr")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for _ in range(2):
            e = tarfile.TarInfo("aicr")
            e.size = 1
            tar.addfile(e, io.BytesIO(b"a"))
    with pytest.raises(native.BaselineError, match="exactly one"):
        native.extract_one_binary(buf.getvalue(), "aicr", tmp_path / "aicr")


def test_binary_extraction_success(tmp_path):
    target=tmp_path/"aicr"
    assert native.extract_one_binary(_tgz(), "aicr", target) == target
    assert target.read_bytes() == b"TEST-ELF-BYTES"


def test_native_command_failure_fails_closed():
    with pytest.raises(native.BaselineError, match="native test unavailable"):
        native.run_required(["/nonexistent-g4-baseline-binary"])


def test_no_implicit_go_flag():
    source=Path(native.__file__).read_text()
    assert '"g4_completed": False' in source and '"decision": "PAUSE_PRODUCT_BUILD"' in source
