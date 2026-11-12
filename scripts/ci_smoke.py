"""Network-free process-level contract smoke test for the public CPU-only CI job.

Fixtures are synthetic, demo keys ephemeral, and the generated trust anchor is NOT
externally secured. This tests exit codes + fail-closed semantics, not real AI execution.
"""
from __future__ import annotations

import json
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
    assert invoke("evaluate", *flags, "--observation", fixture / "clean.json", code=0, status="OK")["rules"] == []
    drift = invoke("evaluate", *flags, "--observation", fixture / "model-drift.json", code=2, status="DRIFT")
    assert "MODEL_DIGEST_MISMATCH" in drift["rules"]
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

    with TemporaryDirectory(prefix="ral-ci-") as tmp:
        out = Path(tmp)
        generated = invoke("demo", "--fixtures", fixture, "--output", out, code=0)
        assert generated["chain_verified"] and generated["cases"] == 7
        verify_args = ("--trust", out / "trust-public.json", "--checkpoint", out / "checkpoint.json")
        good = invoke("verify", "--journal", out / "journal.json", *verify_args, code=0)
        assert good == {"verified": True, "reason": "DECISIONS_RECOMPUTED"}
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
        assert measured["source_forgery_probe"]["unsafe_ok_possible_when_input_source_is_untrusted"]
        assert measured["source_forgery_probe"]["security_gate_passed"] is False

        records = json.loads((out / "journal.json").read_text(encoding="utf-8"))
        records[1]["payload"]["model_digest"] = "sha256:" + "0" * 64
        modified = out / "mutated.json"
        modified.write_text(json.dumps(records), encoding="utf-8")
        bad = invoke("verify", "--journal", modified, *verify_args, code=2)
        assert bad["verified"] is False

    print(json.dumps({
        "offline_smoke": "pass",
        "cases": ["clean", "drift", "stale", "aibom-unknown", "aicr-aibom-unknown", "receipt-replay-and-false-OK-rejected", "same-input-negative-control", "signed-demo", "tamper-rejected"],
        "scope": "synthetic CPU-only; no cluster, no anchored trust root",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
