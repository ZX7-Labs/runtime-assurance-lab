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

    with TemporaryDirectory(prefix="ral-ci-") as tmp:
        out = Path(tmp)
        generated = invoke("demo", "--fixtures", fixture, "--output", out, code=0)
        assert generated["chain_verified"] and generated["cases"] == 7
        verify_args = ("--trust", out / "trust-public.json", "--checkpoint", out / "checkpoint.json")
        good = invoke("verify", "--journal", out / "journal.json", *verify_args, code=0)
        assert good == {"verified": True, "reason": "DECISIONS_RECOMPUTED"}
        records = json.loads((out / "journal.json").read_text(encoding="utf-8"))
        records[1]["payload"]["model_digest"] = "sha256:" + "0" * 64
        modified = out / "mutated.json"
        modified.write_text(json.dumps(records), encoding="utf-8")
        bad = invoke("verify", "--journal", modified, *verify_args, code=2)
        assert bad["verified"] is False

    print(json.dumps({
        "offline_smoke": "pass",
        "cases": ["clean", "drift", "stale", "aibom-unknown", "signed-demo", "tamper-rejected"],
        "scope": "synthetic CPU-only; no cluster, no anchored trust root",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
