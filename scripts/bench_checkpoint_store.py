"""Bounded local SQLite + Ed25519 synthetic checkpoint benchmark (not G4)."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
import time
import tracemalloc

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from runtime_assurance_lab.checkpoint_store import bootstrap, consume
from runtime_assurance_lab.evidence import canonical
from runtime_assurance_lab.source_auth import DOMAIN, GENESIS_HEAD, PROOF_SCHEMA, TRUST_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 12, 3, 25, tzinfo=timezone.utc)


def sha(data: bytes) -> str:
    return "sha256:" + sha256(data).hexdigest()


def percentile(values: list[int], percentile_n: int) -> float:
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) * percentile_n // 100] / 1000.0


def benchmark(samples: int = 100) -> dict[str, object]:
    if not 1 <= samples <= 2000:
        raise ValueError("samples must be 1..2000")
    signer = Ed25519PrivateKey.generate()  # ephemeral benchmark key, never written
    public = signer.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    intent_bytes = (ROOT / "fixtures" / "intent.json").read_bytes()
    observation = json.loads((ROOT / "fixtures" / "clean.json").read_bytes())
    observation["source"] = "synthetic-benchmark-source"
    obs_bytes = canonical(observation)
    auth_bytes = canonical({"schema": TRUST_SCHEMA, "source_id": "synthetic-benchmark-source",
                            "key_id": "temporary", "public_key_ed25519": base64.b64encode(public).decode(),
                            "workloads": ["lab/demo"]})
    intent_pin, authority_pin = sha(intent_bytes), sha(auth_bytes)
    recorded: list[int] = []
    with TemporaryDirectory(prefix="ral-checkpoint-bench-") as scratch:
        db = Path(scratch) / "checkpoints.sqlite"
        independent_pin = bootstrap(db, source_id="synthetic-benchmark-source", workload_id="lab/demo",
                                    expected_authority_sha256=authority_pin, expected_intent_sha256=intent_pin)
        prior = GENESIS_HEAD
        cpu_start = time.process_time_ns()
        tracemalloc.start()
        try:
            for sequence in range(1, samples + 1):
                signable = {"schema": PROOF_SCHEMA, "domain": DOMAIN,
                            "source_id": "synthetic-benchmark-source", "key_id": "temporary",
                            "sequence": sequence, "prev_head": prior, "observation_sha256": sha(obs_bytes),
                            "workload": "lab/demo", "observed_at": observation["observed_at"]}
                proof = canonical({**signable, "signature": base64.b64encode(signer.sign(canonical(signable))).decode()})
                start = time.perf_counter_ns()
                result = consume(db, source_id="synthetic-benchmark-source", workload_id="lab/demo",
                                 expected_state_sha256=independent_pin,
                                 expected_authority_sha256=authority_pin, expected_intent_sha256=intent_pin,
                                 intent_bytes=intent_bytes, authority_bytes=auth_bytes,
                                 observation_bytes=obs_bytes, attestation_bytes=proof, now=NOW)
                recorded.append(time.perf_counter_ns() - start)
                if not result.committed or result.assessment.finding.status != "OK":
                    raise AssertionError("fixture sequence was rejected")
                prior = result.assessment.next_checkpoint["last_head"]
                independent_pin = result.new_state_sha256
            _, heap = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        cpu_ms = (time.process_time_ns() - cpu_start) / 1e6
    return {"samples": samples,
            "operation": "local SQLite BEGIN IMMEDIATE, source-auth verify, synchronous FULL commit",
            "median_us": round(median(recorded) / 1000, 3),
            "p95_us": round(percentile(recorded, 95), 3),
            "p99_us": round(percentile(recorded, 99), 3),
            "max_us": round(max(recorded) / 1000, 3),
            "cpu_ms": round(cpu_ms, 3), "traced_python_heap_peak_bytes": heap,
            "scope": "synthetic local filesystem, sequential, ephemeral signer; NOT live/cluster overhead, external anchoring or crash guarantee"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "checkpoint_store_benchmark.json")
    args = parser.parse_args()
    result = benchmark(args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
