"""Signed source assertion vs unsigned, forged, unanchored, replayed evidence."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from runtime_assurance_lab.contracts import Intent, Observation
from runtime_assurance_lab.evidence import canonical, generate_signer
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from runtime_assurance_lab.evaluate import evaluate
from runtime_assurance_lab.source_auth import (
    DOMAIN, GENESIS_HEAD, PROOF_SCHEMA, TRUST_SCHEMA, authenticate_and_evaluate,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 12, 3, 25, tzinfo=timezone.utc)


def jsonbytes(data):
    return canonical(data)


def sha(data):
    return "sha256:" + sha256(data).hexdigest()


def make_source(*, sequence=1, previous=GENESIS_HEAD, source="approved-fixture-source",
                observation_change=None, signer=None, authority_key=None):
    intent_bytes = (ROOT / "fixtures/intent.json").read_bytes()
    observation = json.loads((ROOT / "fixtures/clean.json").read_text())
    observation["source"] = source
    if observation_change:
        observation.update(observation_change)
    observation_bytes = jsonbytes(observation)
    if signer is None:
        # Public, deterministic TEST-ONLY seed; never a deployable key.
        key = Ed25519PrivateKey.from_private_bytes(sha256(b"ral-fixture-not-a-secret-ed25519-key").digest())
        public = base64.b64encode(key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii")
    else:
        key, public = signer
    approved_public = authority_key or public
    trust_bytes = jsonbytes({"schema": TRUST_SCHEMA, "source_id": source, "key_id": "collector-v1",
                             "public_key_ed25519": approved_public, "workloads": ["lab/demo"]})
    payload = {"schema": PROOF_SCHEMA, "domain": DOMAIN, "source_id": source, "key_id": "collector-v1",
               "sequence": sequence, "prev_head": previous,
               "observation_sha256": sha(observation_bytes), "workload": observation["workload"],
               "observed_at": observation["observed_at"]}
    proof = {**payload, "signature": base64.b64encode(key.sign(canonical(payload))).decode("ascii")}
    return {"intent_bytes": intent_bytes, "observation_bytes": observation_bytes,
            "attestation_bytes": jsonbytes(proof), "authority_bytes": trust_bytes,
            "expected_intent_sha256": sha(intent_bytes), "expected_authority_sha256": sha(trust_bytes),
            "expected_sequence": sequence, "expected_prev_head": previous, "now": NOW}


def check(**kwargs):
    return authenticate_and_evaluate(**kwargs)


def test_reproduce_forged_matching_verified_untrusted_never_ok():
    doc = json.loads((ROOT/"fixtures/clean.json").read_text())
    intent = Intent.parse(json.loads((ROOT/"fixtures/intent.json").read_text()))
    claim = Observation.parse(doc)
    # Hidden runtime truth can differ; untrusted caller controls every normalized field.
    result = evaluate(intent, claim, now=NOW)
    assert result.status == "UNKNOWN"
    assert result.rules == ("SOURCE_AUTHENTICITY_UNVERIFIED",)


def test_legitimate_independently_pinned_source_and_next_checkpoint():
    material = make_source()
    result = check(**material)
    assert result.source_authenticated is True
    assert result.finding.status == "OK"
    assert result.next_checkpoint["next_sequence"] == 2
    assert result.next_checkpoint["last_head"].startswith("sha256:")
    # Consuming the same signed sequence with the externally persisted checkpoint fails.
    rechecked = check(**{**material, "expected_sequence": 2,
                         "expected_prev_head": result.next_checkpoint["last_head"]})
    assert rechecked.finding.status == "UNKNOWN"
    assert not rechecked.source_authenticated
    assert rechecked.finding.rules == ("SOURCE_REPLAY_OR_SEQUENCE_GAP",)


def test_monotonic_chain_valid_second_attestation():
    key, pub = generate_signer()
    # New scenario with the same independently pinned key material.
    one = make_source(sequence=1, signer=(key, pub))
    first = check(**one)
    two = make_source(sequence=2, previous=first.next_checkpoint["last_head"], signer=(key, pub))
    next_result = check(**two)
    assert next_result.finding.status == "OK"
    assert next_result.next_checkpoint["next_sequence"] == 3
    old_again = check(**{**one, "expected_sequence": 3,
                         "expected_prev_head": next_result.next_checkpoint["last_head"]})
    assert not old_again.source_authenticated


def test_authenticated_source_reports_real_mismatch_only_after_signature():
    material = make_source(observation_change={"model_digest": "sha256:" + "b" * 64})
    result = check(**material)
    assert result.source_authenticated and result.finding.status == "DRIFT"
    assert "MODEL_DIGEST_MISMATCH" in result.finding.rules


@pytest.mark.parametrize("attack,reason", [
    ("tamper_raw", "SOURCE_PAYLOAD_TAMPERED"),
    ("tamper_signature", "SOURCE_SIGNATURE_INVALID"),
    ("forge_signer", "SOURCE_SIGNATURE_INVALID"),
    ("replace_key_and_authority", "TRUST_ROOT_NOT_ANCHORED"),
    ("wrong_intent_pin", "intent pin mismatch"),
    ("wrong_workload", "SOURCE_IDENTITY_MISBOUND"),
    ("wrong_source", "SOURCE_IDENTITY_MISBOUND"),
    ("wrong_time", "SOURCE_TIMESTAMP_MISBOUND"),
    ("replay", "SOURCE_REPLAY_OR_SEQUENCE_GAP"),
    ("rollback", "SOURCE_ROLLBACK_OR_FORK"),
    ("sequence_gap", "SOURCE_REPLAY_OR_SEQUENCE_GAP"),
    ("same_authority_self_attestation", "TRUST_ROOT_NOT_ANCHORED"),
    ("bad_attestation", "SOURCE_EVIDENCE_INVALID"),
    ("extra_attestation_claim", "SOURCE_PROOF_INVALID"),
])
def test_attacks_fail_closed(attack, reason):
    material = make_source()
    if attack == "tamper_raw":
        data = json.loads(material["observation_bytes"])
        data["model_digest"] = "sha256:" + "0" * 64
        material["observation_bytes"] = jsonbytes(data)
    elif attack == "tamper_signature":
        data = json.loads(material["attestation_bytes"])
        data["signature"] = base64.b64encode(b"x" * 64).decode()
        material["attestation_bytes"] = jsonbytes(data)
    elif attack == "forge_signer":
        fake, _ = generate_signer()
        data = json.loads(material["attestation_bytes"])
        data["signature"] = base64.b64encode(fake.sign(canonical({k:v for k,v in data.items() if k != "signature"}))).decode()
        material["attestation_bytes"] = jsonbytes(data)
    elif attack in ("replace_key_and_authority", "same_authority_self_attestation"):
        attacker_key, attacker_pub = generate_signer()
        other = make_source(signer=(attacker_key, attacker_pub))
        material["attestation_bytes"] = other["attestation_bytes"]
        material["authority_bytes"] = other["authority_bytes"]
        # Original separately pinned authority digest intentionally unchanged.
    elif attack == "wrong_intent_pin":
        material["expected_intent_sha256"] = "sha256:" + "0" * 64
    elif attack in ("wrong_workload", "wrong_source", "wrong_time"):
        data = json.loads(material["observation_bytes"])
        if attack == "wrong_workload": data["workload"] = "lab/other"
        if attack == "wrong_source": data["source"] = "malicious-producer"
        if attack == "wrong_time": data["observed_at"] = "2026-11-12T03:25:08Z"
        material["observation_bytes"] = jsonbytes(data)
        # Changed unsigned JSON is rejected for identity or byte binding.
        if attack == "wrong_time":
            reason = "SOURCE_PAYLOAD_TAMPERED"
    elif attack == "replay":
        material["expected_sequence"] = 2
        material["expected_prev_head"] = "sha256:" + "a" * 64
    elif attack == "rollback":
        material = make_source(sequence=2, previous="sha256:" + "e" * 64)
        material["expected_prev_head"] = "sha256:" + "f" * 64
    elif attack == "sequence_gap":
        material["expected_sequence"] = 0  # external checkpoint validation fails
    elif attack == "bad_attestation":
        material["attestation_bytes"] = b'{"x":1,"x":2}'
    elif attack == "extra_attestation_claim":
        data = json.loads(material["attestation_bytes"])
        data["production_ready"] = True
        material["attestation_bytes"] = jsonbytes(data)
    if attack in ("wrong_intent_pin", "sequence_gap"):
        with pytest.raises(ValueError, match=reason if attack == "wrong_intent_pin" else "expected_sequence"):
            check(**material)
    else:
        result = check(**material)
        assert not result.source_authenticated
        assert result.finding.status == "UNKNOWN"
        assert result.finding.rules == (reason,)
        assert result.next_checkpoint is None


def test_signed_but_stale_is_not_current_assurance():
    material = make_source(observation_change={"observed_at": (NOW - timedelta(minutes=10)).isoformat()})
    result = check(**material)
    assert result.source_authenticated and result.finding.status == "STALE"


def test_claimed_verified_without_root_or_checkpoint_cannot_invent_ok():
    material = make_source()
    assert check(**{**material, "expected_authority_sha256": "sha256:" + "0"*64}).finding.status == "UNKNOWN"
    with pytest.raises(TypeError):
        # Missing independently held checkpoint inputs is not a permissible default.
        authenticate_and_evaluate(intent_bytes=material["intent_bytes"], observation_bytes=material["observation_bytes"])


def test_cli_authenticated_positive_and_rollback(tmp_path):
    material = make_source()
    paths = {}
    for name in ("intent_bytes", "observation_bytes", "attestation_bytes", "authority_bytes"):
        path = tmp_path / (name + ".json")
        path.write_bytes(material[name])
        paths[name] = path
    options = ["--intent", str(paths["intent_bytes"]), "--observation", str(paths["observation_bytes"]),
               "--attestation", str(paths["attestation_bytes"]), "--authority", str(paths["authority_bytes"]),
               "--expected-intent-sha256", material["expected_intent_sha256"],
               "--expected-authority-sha256", material["expected_authority_sha256"],
               "--expected-sequence", "1", "--expected-prev-head", GENESIS_HEAD,
               "--now", "2026-11-12T03:25:00Z"]
    def cmd(args):
        return subprocess.run([sys.executable, "-m", "runtime_assurance_lab.cli", "evaluate-authenticated", *args],
                              cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT/"src")}, capture_output=True, text=True)
    good = cmd(options)
    assert good.returncode == 0, good.stderr
    parsed = json.loads(good.stdout)
    assert parsed["source_authenticated"] and parsed["status"] == "OK"
    assert parsed["next_checkpoint"]["next_sequence"] == 2
    options[options.index("--expected-sequence")+1] = "2"
    options[options.index("--expected-prev-head")+1] = parsed["next_checkpoint"]["last_head"]
    rejected = cmd(options)
    assert rejected.returncode == 2
    assert json.loads(rejected.stdout)["status"] == "UNKNOWN"


def test_independently_signed_different_timestamp_does_not_gain_freshness():
    key, pub = generate_signer()
    m = make_source(signer=(key, pub))
    record = json.loads(m["attestation_bytes"])
    # Same raw bytes and valid signature, but signed timestamp conflicts with
    # the payload's observed_at (a signer error or compromise).
    record["observed_at"] = "2026-11-12T03:25:09Z"
    record["signature"] = base64.b64encode(key.sign(canonical({k:v for k,v in record.items() if k!="signature"}))).decode()
    result = check(**{**m, "attestation_bytes": jsonbytes(record)})
    assert result.finding.status == "UNKNOWN"
    assert result.finding.rules == ("SOURCE_TIMESTAMP_MISBOUND",)


def test_signed_forged_source_identity_and_workload_are_not_authorized():
    key, pub = generate_signer()
    m = make_source(signer=(key, pub))
    for field, wrong in (("source_id", "evil-collector"), ("workload", "lab/other"), ("key_id", "other-key")):
        proof = json.loads(m["attestation_bytes"])
        proof[field] = wrong
        proof["signature"] = base64.b64encode(key.sign(canonical({k:v for k,v in proof.items() if k != "signature"}))).decode()
        result = check(**{**m, "attestation_bytes": jsonbytes(proof)})
        assert result.finding.status == "UNKNOWN"
        assert result.finding.rules == ("SOURCE_IDENTITY_MISBOUND",)


def test_pinned_authority_rejects_revocation_replacement_or_wider_scope():
    m = make_source()
    attacker_authority = json.loads(m["authority_bytes"])
    attacker_authority["workloads"].append("lab/other")
    result = check(**{**m, "authority_bytes": jsonbytes(attacker_authority)})
    assert result.finding.rules == ("TRUST_ROOT_NOT_ANCHORED",)
    assert not result.source_authenticated


def test_signed_claim_is_still_unknown_when_model_identity_is_not_verified():
    m = make_source(observation_change={"model_confidence": "declared"})
    result = check(**m)
    assert result.source_authenticated
    assert result.finding.status == "UNKNOWN"
    assert "MODEL_NOT_CRYPTO_VERIFIED" in result.finding.rules


def test_valid_but_future_signed_assertion_is_indeterminate():
    m = make_source(observation_change={"observed_at": (NOW + timedelta(seconds=35)).isoformat()})
    result = check(**m)
    assert result.source_authenticated and result.finding.status == "UNKNOWN"
    assert "FUTURE_OBSERVATION" in result.finding.rules


def test_boolean_sequence_in_signed_record_fails_closed():
    m = make_source()
    bad = json.loads(m["attestation_bytes"])
    bad["sequence"] = True
    result = check(**{**m, "attestation_bytes": jsonbytes(bad)})
    assert not result.source_authenticated and result.finding.status == "UNKNOWN"


def test_bad_root_bad_pinned_digest_and_missing_clock_fail_closed():
    m = make_source()
    with pytest.raises(ValueError, match="timezone"):
        check(**{**m, "now": NOW.replace(tzinfo=None)})
    with pytest.raises(ValueError, match="expected_sequence"):
        check(**{**m, "expected_sequence": True})
    with pytest.raises(ValueError, match="digest"):
        check(**{**m, "expected_prev_head": "self-attested"})
    bad = json.loads(m["authority_bytes"])
    bad["public_key_ed25519"] = "%%%"
    raw = jsonbytes(bad)
    result = check(**{**m, "authority_bytes": raw, "expected_authority_sha256": sha(raw)})
    assert not result.source_authenticated and result.finding.status == "UNKNOWN"


def test_trusted_but_dishonest_signer_remains_a_residual_risk_not_execution_proof():
    # Even with a valid independent public-key pin, a malicious/compromised
    # *authorized* collector can sign false runtime assertions. A signature
    # establishes origin/key control, NOT observation truth. G4 must verify
    # actual upstream attestations and enforcement scope.
    m = make_source()
    result = check(**m)
    assert result.source_authenticated and result.finding.status == "OK"
    assert result.to_dict()["scope"].endswith("NOT proof of running model/GPU")


def test_genesis_cannot_be_reused_for_noninitial_sequence():
    m = make_source(sequence=2)
    with pytest.raises(ValueError, match="genesis"):
        check(**m)
