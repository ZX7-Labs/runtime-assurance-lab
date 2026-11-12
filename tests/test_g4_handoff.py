"""Adversarial offline checks: handoff integrity is never source authenticity."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import os
import subprocess
import sys

import pytest

from runtime_assurance_lab.g4_handoff import (
    MAX_RAW_BYTES, REQUIRED_SOURCES, SCHEMA, inspect_handoff,
)
from runtime_assurance_lab.json_strict import loads_strict

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
SCRIPT = ROOT / "scripts/run_g4_handoff.py"
PATHS = {
    "intent_bytes": FIXTURES / "intent-aicr-synthetic.json",
    "recipe_bytes": FIXTURES / "aicr-recipe-result-synthetic.json",
    "aibom_bytes": FIXTURES / "aibom-v1beta1-synthetic.json",
}
PINS = {
    "intent_bytes": "expected_intent_sha256",
    "recipe_bytes": "expected_recipe_sha256",
    "aibom_bytes": "expected_aibom_sha256",
}


def _samples() -> dict[str, bytes | str]:
    raw = {key: path.read_bytes() for key, path in PATHS.items()}
    return {**raw, **{pin: "sha256:" + sha256(raw[key]).hexdigest()
                     for key, pin in PINS.items()}}


def _replace(payload: dict[str, bytes | str], name: str, data: object) -> dict[str, bytes | str]:
    out = payload.copy()
    out[name] = json.dumps(data, sort_keys=True).encode("utf-8")
    out[PINS[name]] = "sha256:" + sha256(out[name]).hexdigest()
    return out


def _run(tmp_path: Path, *, payload: dict[str, bytes | str] | None = None,
         file_paths: dict[str, Path] | None = None, output: Path | None = None) -> subprocess.CompletedProcess:
    p = payload or _samples()
    inputs = {}
    for key in PATHS:
        if file_paths and key in file_paths:
            inputs[key] = file_paths[key]
        else:
            file = tmp_path / (key + ".json")
            file.write_bytes(p[key])
            inputs[key] = file
    args = [sys.executable, str(SCRIPT)]
    for key in PATHS:
        args.extend(["--" + key.removesuffix("_bytes").replace("_bytes", ""), str(inputs[key])])
        args.extend(["--expected-" + key.removesuffix("_bytes") + "-sha256", p[PINS[key]]])
    if output is not None:
        args.extend(["--output", str(output)])
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)


def test_successful_fixture_remains_untrusted_and_does_not_echo_names():
    report = inspect_handoff(**_samples())
    assert report["schema"] == SCHEMA
    assert report["handoff_state"] == "STRUCTURALLY_COMPATIBLE_UNAUTHENTICATED"
    assert report["decision"] == "PAUSE_PRODUCT_BUILD"
    assert report["artifact_byte_pins_match"] is True
    for key in ("authentic_upstream_provenance_verified", "pins_established_independently",
                "cross_plane_runtime_binding_verified", "runtime_model_execution_attested", "g4_authorized"):
        assert report[key] is False
    serialized = json.dumps(report)
    assert "lab/demo" not in serialized
    assert "hf://lab/approved" not in serialized
    assert set(report["sources"]) == {"aibom", "aicr_recipe", "intent"}
    assert REQUIRED_SOURCES == ("intent", "recipe", "aibom")


@pytest.mark.parametrize("which", ["intent_bytes", "recipe_bytes", "aibom_bytes"])
@pytest.mark.parametrize("method", ["tamper", "reformat", "blank", "oversized"])
def test_corrupted_source_cannot_override_external_pin(which, method):
    payload = _samples()
    raw = payload[which]
    if method == "tamper":
        payload[which] = raw + b" "
    elif method == "reformat":
        payload[which] = json.dumps(loads_strict(raw), indent=5).encode()
    elif method == "blank":
        payload[which] = b""
    else:
        payload[which] = b"x" * (MAX_RAW_BYTES + 1)
    with pytest.raises(ValueError):
        inspect_handoff(**payload)


def test_malicious_source_controls_all_pins_but_cannot_get_go():
    payload = _samples()
    original = loads_strict(payload["aibom_bytes"])
    original["status"]["summary"]["models"][0]["signed"] = "verified"
    original["metadata"]["secret"] = "SUPERSECRET_CREDENTIAL_DO_NOT_EXPORT"
    payload = _replace(payload, "aibom_bytes", original)
    report = inspect_handoff(**payload)
    assert report["decision"] == "PAUSE_PRODUCT_BUILD"
    assert report["g4_authorized"] is False
    assert "SUPERSECRET_CREDENTIAL_DO_NOT_EXPORT" not in json.dumps(report)


def test_raw_field_bomb_nonfinite_or_duplicate_rejected_even_with_matching_pin():
    for suffix in (b',"kind":"AIBOM"}', b',"evil":1e999}', b',"evil":NaN}'):
        payload = _samples()
        data = payload["aibom_bytes"].rstrip()[:-1] + suffix
        payload["aibom_bytes"] = data
        payload["expected_aibom_sha256"] = "sha256:" + sha256(data).hexdigest()
        with pytest.raises(ValueError):
            inspect_handoff(**payload)


def test_wrong_workload_yields_blocked_structural_conflict_without_echo():
    payload = _samples()
    resource = loads_strict(payload["aibom_bytes"])
    resource["spec"]["workloadRef"]["name"] = "other"
    resource["status"]["summary"]["workload"]["name"] = "other"
    payload = _replace(payload, "aibom_bytes", resource)
    report = inspect_handoff(**payload)
    assert report["handoff_state"] == "BLOCKED_WORKLOAD_IDENTITY_CONFLICT"
    assert report["g4_authorized"] is False
    assert "other" not in json.dumps(report)


def test_incomplete_inventory_rejects_evidence_as_ready():
    payload = _samples()
    resource = loads_strict(payload["aibom_bytes"])
    resource["status"]["conditions"][0]["status"] = "False"
    payload = _replace(payload, "aibom_bytes", resource)
    report = inspect_handoff(**payload)
    assert report["handoff_state"] == "BLOCKED_INCOMPLETE_AIBOM"
    assert report["aibom"]["observation_available"] is False
    assert report["decision"] == "PAUSE_PRODUCT_BUILD"


@pytest.mark.parametrize("which", ["intent_bytes", "recipe_bytes", "aibom_bytes"])
def test_schema_confusion_fails_closed(which):
    payload = _samples()
    payload = _replace(payload, which, {"untrusted": "verified"})
    with pytest.raises(ValueError):
        inspect_handoff(**payload)


def test_invalid_external_pin_rejected():
    payload = _samples()
    payload["expected_recipe_sha256"] = "sha256:" + "F" * 64
    with pytest.raises(ValueError):
        inspect_handoff(**payload)


def test_cli_successful_structural_preflight_is_nonzero(tmp_path):
    run = _run(tmp_path)
    assert run.returncode == 2
    report = json.loads(run.stdout)
    assert report["decision"] == "PAUSE_PRODUCT_BUILD"
    assert report["g4_authorized"] is False
    assert run.stderr == ""


def test_cli_exclusive_report_output_private_and_sanitized(tmp_path):
    target = tmp_path / "report.json"
    run = _run(tmp_path, output=target)
    assert run.returncode == 2
    assert stat_mode(target) == 0o600
    assert json.loads(target.read_text()) == json.loads(run.stdout)
    again = _run(tmp_path, output=target)
    assert again.returncode == 3
    assert json.loads(target.read_text()) == json.loads(run.stdout)


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


@pytest.mark.parametrize("bad", ["missing", "directory", "symlink"])
def test_cli_rejects_absent_nonregular_or_symlink(tmp_path, bad):
    source = tmp_path / "bad"
    if bad == "directory":
        source.mkdir()
    if bad == "symlink":
        source.symlink_to(PATHS["intent_bytes"])
    run = _run(tmp_path, file_paths={"intent_bytes": source})
    assert run.returncode == 3
    report = json.loads(run.stdout)
    assert report["decision"] == "INVALID_OR_UNTRUSTED_HANDOFF"
    assert report["g4_authorized"] is False
    assert str(source) not in run.stdout


def test_cli_tampered_pin_is_error_not_approval(tmp_path):
    payload = _samples()
    payload["expected_intent_sha256"] = "sha256:" + "0" * 64
    run = _run(tmp_path, payload=payload)
    assert run.returncode == 3
    assert json.loads(run.stdout)["decision"] == "INVALID_OR_UNTRUSTED_HANDOFF"


def test_cli_no_dump_of_sensitive_model_name_on_error(tmp_path):
    payload = _samples()
    intent = loads_strict(payload["intent_bytes"])
    intent["model_ref"] = "SENSITIVE_MODEL_ID_THIS_MUST_NOT_LEAK"
    payload = _replace(payload, "intent_bytes", intent)
    run = _run(tmp_path, payload=payload)
    assert run.returncode == 2  # valid structure, but never authenticated
    assert json.loads(run.stdout)["g4_authorized"] is False
    assert "SENSITIVE_MODEL_ID_THIS_MUST_NOT_LEAK" not in (run.stdout + run.stderr)


def test_model_mismatch_is_not_declared_structurally_compatible():
    payload = _samples()
    resource = loads_strict(payload["aibom_bytes"])
    resource["status"]["summary"]["models"][0]["identity"] = "hf://other/private"
    payload = _replace(payload, "aibom_bytes", resource)
    result = inspect_handoff(**payload)
    assert result["handoff_state"] == "BLOCKED_MODEL_CLAIM_CONFLICT"
    assert result["g4_authorized"] is False


def test_unresolved_model_is_not_structurally_compatible():
    payload = _samples()
    resource = loads_strict(payload["aibom_bytes"])
    resource["status"]["summary"]["models"] = []
    payload = _replace(payload, "aibom_bytes", resource)
    result = inspect_handoff(**payload)
    assert result["handoff_state"] == "BLOCKED_MODEL_IDENTITY_UNRESOLVED"
    assert result["g4_authorized"] is False


def test_recipe_category_conflict_is_not_accepted():
    payload = _samples()
    resource = loads_strict(payload["aibom_bytes"])
    resource["status"]["summary"]["workload"]["category"] = "training"
    payload = _replace(payload, "aibom_bytes", resource)
    result = inspect_handoff(**payload)
    assert result["handoff_state"] == "BLOCKED_WORKLOAD_CATEGORY_CONFLICT"
    assert result["g4_authorized"] is False


def test_recorded_synthetic_handoff_report_is_recomputable():
    recorded = loads_strict((ROOT / "results/g4_handoff_synthetic.json").read_bytes())
    expected = inspect_handoff(**_samples())
    assert json.dumps(recorded, sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert recorded["decision"] == "PAUSE_PRODUCT_BUILD"


def test_cli_output_symlink_does_not_follow_or_modify_target(tmp_path):
    protected = tmp_path / "operator-owned.txt"
    protected.write_text("DO_NOT_OVERWRITE", encoding="utf-8")
    report_link = tmp_path / "report.json"
    report_link.symlink_to(protected)
    run = _run(tmp_path, output=report_link)
    assert run.returncode == 3
    assert protected.read_text(encoding="utf-8") == "DO_NOT_OVERWRITE"
    assert json.loads(run.stdout)["g4_authorized"] is False


def test_cli_fifo_source_is_rejected_without_hanging(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("requires POSIX named pipes")
    pipe = tmp_path / "untrusted.fifo"
    os.mkfifo(pipe)
    run = _run(tmp_path, file_paths={"intent_bytes": pipe})
    assert run.returncode == 3
    assert json.loads(run.stdout)["decision"] == "INVALID_OR_UNTRUSTED_HANDOFF"


def test_replay_of_same_structural_handoff_never_grants_authenticity():
    payload = _samples()
    first = inspect_handoff(**payload)
    replay = inspect_handoff(**payload)
    assert json.dumps(first, sort_keys=True) == json.dumps(replay, sort_keys=True)
    assert first["decision"] == "PAUSE_PRODUCT_BUILD"
    assert first["g4_authorized"] is False
    assert replay["g4_authorized"] is False
