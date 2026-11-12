"""Network-free process-level contract smoke test for the public CPU-only CI job.

Fixtures are synthetic, demo keys ephemeral, and the generated trust anchor is NOT
externally secured. This tests exit codes + fail-closed semantics, not real AI execution.
"""
from __future__ import annotations

import json
import base64
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from runtime_assurance_lab.evidence import canonical
from runtime_assurance_lab.source_auth import DOMAIN, PROOF_SCHEMA, TRUST_SCHEMA, GENESIS_HEAD
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-11-12T03:25:00Z"


def invoke(*args: object, code: int, status: str | None = None) -> dict:
    run = subprocess.run(
        [sys.executable, "-m", "runtime_assurance_lab.cli", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    if run.returncode != code:
        raise AssertionError(f"{args[0]}: expected exit {code}, got {run.returncode}; stderr={run.stderr[:1000]}")
    if run.stderr:
        raise AssertionError(f"{args[0]} wrote unexpected stderr: {run.stderr[:1000]}")
    obj = json.loads(run.stdout)
    if status is not None and obj.get("status") != status:
        raise AssertionError(f"{args[0]}: expected {status}, got {obj.get('status')}")
    return obj


def main() -> None:
    fixture = ROOT / "fixtures"
    flags = ("--intent", fixture / "intent.json", "--now", STAMP)
    assert invoke("evaluate", *flags, "--observation", fixture / "clean.json", code=2, status="UNKNOWN")["rules"] == ["SOURCE_AUTHENTICITY_UNVERIFIED"]
    drift = invoke("evaluate", *flags, "--observation", fixture / "model-drift.json", code=2, status="UNKNOWN")
    assert "SOURCE_AUTHENTICITY_UNVERIFIED" in drift["rules"]
    invoke("evaluate", *flags, "--observation", fixture / "stale.json", code=2, status="STALE")
    aibom = invoke(
        "evaluate-aibom", *flags, "--aibom", fixture / "aibom-v1beta1-synthetic.json", code=2, status="UNKNOWN"
    )
    assert aibom["adapter"]["limitations"], "AIBOM must preserve missing trust inputs"

    pinned = json.loads((fixture / "intent-aicr-synthetic.json").read_text(encoding="utf-8"))
    combined = invoke(
        "correlate-offline", "--intent", fixture / "intent-aicr-synthetic.json",
        "--recipe", fixture / "aicr-recipe-result-synthetic.json",
        "--expected-recipe-sha256", pinned["platform_recipe_digest"],
        "--aibom", fixture / "aibom-v1beta1-synthetic.json",
        "--now", STAMP, code=2, status="UNKNOWN",
    )
    assert combined["sources"]["aicr"]["sha256"] == pinned["platform_recipe_digest"]
    assert "AICR_RECIPE_NOT_DEPLOYMENT_PROOF" in combined["sources"]["aicr"]["limitations"]

    # G4 operator intake is an integrity-only preflight: even fully matching
    # pinned synthetic files MUST NOT exit successfully or grant G4 approval.
    handoff_args = [sys.executable, str(ROOT / "scripts" / "run_g4_handoff.py")]
    for name, filename in (("intent", "intent-aicr-synthetic.json"),
                           ("recipe", "aicr-recipe-result-synthetic.json"),
                           ("aibom", "aibom-v1beta1-synthetic.json")):
        raw = (fixture / filename).read_bytes()
        handoff_args.extend([f"--{name}", str(fixture / filename),
                             f"--expected-{name}-sha256", "sha256:" + sha256(raw).hexdigest()])
    intact = subprocess.run(handoff_args, cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert intact.returncode == 2 and not intact.stderr
    intact_report = json.loads(intact.stdout)
    assert intact_report["decision"] == "PAUSE_PRODUCT_BUILD"
    assert intact_report["handoff_state"] == "STRUCTURALLY_COMPATIBLE_UNAUTHENTICATED"
    assert intact_report["g4_authorized"] is False
    spoof = handoff_args[:]
    spoof[spoof.index("--expected-aibom-sha256") + 1] = "sha256:" + "0" * 64
    rejected = subprocess.run(spoof, cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert rejected.returncode == 3 and not rejected.stderr
    assert json.loads(rejected.stdout)["decision"] == "INVALID_OR_UNTRUSTED_HANDOFF"

    with TemporaryDirectory(prefix="ral-ci-") as tmp:
        out = Path(tmp)
        generated = invoke("demo", "--fixtures", fixture, "--output", out, code=0)
        assert generated["chain_verified"] and generated["cases"] == 7
        verify_args = ("--trust", out / "trust-public.json", "--checkpoint", out / "checkpoint.json")
        good = invoke("verify", "--journal", out / "journal.json", *verify_args, code=0)
        assert good == {"verified": True, "reason": "DECISIONS_RECOMPUTED"}
        # Offline signed-source control with pinned authority/intent digests and
        # an externally supplied genesis checkpoint (synthetic, NOT external trust).
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        observation = json.loads((fixture / "clean.json").read_bytes())
        observation["source"] = "ephemeral-ci-collector"
        observation_bytes = canonical(observation)
        intent_bytes = (fixture / "intent.json").read_bytes()
        authority_bytes = canonical({"schema": TRUST_SCHEMA, "source_id": "ephemeral-ci-collector",
                                     "key_id": "ci-only-key", "public_key_ed25519": base64.b64encode(public).decode(),
                                     "workloads": ["lab/demo"]})
        signature_content = {"schema": PROOF_SCHEMA, "domain": DOMAIN, "source_id": observation["source"],
                             "key_id": "ci-only-key", "sequence": 1, "prev_head": GENESIS_HEAD,
                             "observation_sha256": "sha256:" + sha256(observation_bytes).hexdigest(),
                             "workload": observation["workload"], "observed_at": observation["observed_at"]}
        attestation_bytes = canonical({**signature_content,
            "signature": base64.b64encode(key.sign(canonical(signature_content))).decode()})
        (out / "source.json").write_bytes(observation_bytes)
        (out / "authority.json").write_bytes(authority_bytes)
        (out / "attestation.json").write_bytes(attestation_bytes)
        auth_flags = ("--intent", fixture / "intent.json", "--observation", out / "source.json",
                      "--authority", out / "authority.json", "--attestation", out / "attestation.json",
                      "--expected-intent-sha256", "sha256:" + sha256(intent_bytes).hexdigest(),
                      "--expected-authority-sha256", "sha256:" + sha256(authority_bytes).hexdigest(),
                      "--expected-sequence", "1", "--expected-prev-head", GENESIS_HEAD, "--now", STAMP)
        authenticated = invoke("evaluate-authenticated", *auth_flags, code=0, status="OK")
        assert authenticated["source_authenticated"] and authenticated["next_checkpoint"]["next_sequence"] == 2
        replay_flags = list(auth_flags)
        replay_flags[replay_flags.index("--expected-sequence") + 1] = "2"
        replay_flags[replay_flags.index("--expected-prev-head") + 1] = authenticated["next_checkpoint"]["last_head"]
        denied = invoke("evaluate-authenticated", *replay_flags, code=2, status="UNKNOWN")
        assert denied["source_authenticated"] is False
        # Transactional checkpoint experiment: the operator keeps the state pin
        # out of the database; old pins must not permit repeat consumption.
        local_db = out / "local-checkpoint.sqlite"
        boot = invoke("checkpoint-init-offline", "--state-db", local_db,
                      "--source-id", "ephemeral-ci-collector", "--workload", "lab/demo",
                      "--expected-authority-sha256", "sha256:" + sha256(authority_bytes).hexdigest(),
                      "--expected-intent-sha256", "sha256:" + sha256(intent_bytes).hexdigest(), code=0)
        assert boot["state_sha256"].startswith("sha256:") and boot["bootstrapped"]
        state_flags = ("--state-db", local_db, "--source-id", "ephemeral-ci-collector",
                       "--workload", "lab/demo", "--expected-state-sha256", boot["state_sha256"],
                       "--intent", fixture / "intent.json", "--observation", out / "source.json",
                       "--authority", out / "authority.json", "--attestation", out / "attestation.json",
                       "--expected-intent-sha256", "sha256:" + sha256(intent_bytes).hexdigest(),
                       "--expected-authority-sha256", "sha256:" + sha256(authority_bytes).hexdigest(),
                       "--now", STAMP)
        committed = invoke("evaluate-authenticated-stateful", *state_flags, code=0, status="OK")
        assert committed["checkpoint_committed"] and committed["new_state_sha256"]
        state_replay = invoke("evaluate-authenticated-stateful", *state_flags, code=2, status="UNKNOWN")
        assert state_replay["rules"] == ["CHECKPOINT_ANCHOR_MISMATCH"]

        # A source-supplied key must not replace an independently pinned root.
        auth_modified = json.loads(authority_bytes)
        auth_modified["workloads"].append("lab/other")
        (out / "authority.json").write_bytes(canonical(auth_modified))
        substituted = invoke("evaluate-authenticated", *auth_flags, code=2, status="UNKNOWN")
        assert substituted["rules"] == ["TRUST_ROOT_NOT_ANCHORED"]

        # Independent raw-source replay of a cross-plane receipt; no upstream attestation.
        receipt = out / "crossplane-receipt.json"
        receipt_flags = (
            "--intent", fixture / "intent-aicr-synthetic.json",
            "--recipe", fixture / "aicr-recipe-result-synthetic.json",
            "--expected-recipe-sha256", pinned["platform_recipe_digest"],
            "--aibom", fixture / "aibom-v1beta1-synthetic.json", "--now", STAMP,
        )
        created = invoke("receipt-offline", *receipt_flags, "--output", receipt, code=0)
        assert created["status"] == "UNKNOWN"
        replayed = invoke("replay-offline", *receipt_flags, "--receipt", receipt, code=0)
        assert replayed["verified_replay"] is True
        forged = json.loads(receipt.read_text(encoding="utf-8"))
        forged["decision"]["status"] = "OK"
        forged_file = out / "forged-receipt.json"
        forged_file.write_text(json.dumps(forged), encoding="utf-8")
        rejected = invoke("replay-offline", *receipt_flags, "--receipt", forged_file, code=2)
        assert rejected["verified_replay"] is False

        # Offline same-input negative control: parity prevents claiming novelty.
        control = out / "incremental_value.json"
        trial = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "bench_incremental_value.py"),
             "--trials", "3", "--output", str(control)],
            cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
        )
        if trial.returncode != 0:
            raise AssertionError(f"negative control failed: {trial.stderr[:1000]}")
        measured = json.loads(control.read_text(encoding="utf-8"))
        assert measured["counts"]["complete_input_reference_disagreements"] == 0
        assert measured["counts"]["unsupported_ok"] == 0
        assert measured["metrics"]["overall_latent_drift_recall"] < 1
        assert measured["interpretation"]["product_differentiation_proven"] is False
        assert not measured["source_forgery_probe"]["unsafe_ok_possible_when_input_source_is_untrusted"]
        assert measured["source_forgery_probe"]["security_gate_passed"] is True

        records = json.loads((out / "journal.json").read_text(encoding="utf-8"))
        records[1]["payload"]["model_digest"] = "sha256:" + "0" * 64
        modified = out / "mutated.json"
        modified.write_text(json.dumps(records), encoding="utf-8")
        bad = invoke("verify", "--journal", modified, *verify_args, code=2)
        assert bad["verified"] is False

    print(json.dumps({
        "offline_smoke": "pass",
        "cases": ["untrusted-clean-unknown", "untrusted-drift-unknown", "authenticated-signed-ok", "signed-replay-rejected", "self-attested-root-rejected", "stale", "aibom-unknown", "aicr-aibom-unknown", "receipt-replay-and-false-OK-rejected", "same-input-negative-control", "signed-demo", "tamper-rejected", "sqlite-checkpoint-consumed", "sqlite-checkpoint-replay-rejected", "g4-handoff-untrusted-no-go", "g4-handoff-external-pin-fail"],
        "scope": "synthetic CPU-only; no cluster, no anchored trust root",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
