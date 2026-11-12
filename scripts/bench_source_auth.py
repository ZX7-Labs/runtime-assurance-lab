"""Offline cryptographic boundary microbenchmark. No trusted runtime/cluster proof.

Usage: PYTHONPATH=src python scripts/bench_source_auth.py --output results/source_auth_benchmark.json
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import time
import tracemalloc

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from runtime_assurance_lab.evidence import canonical
from runtime_assurance_lab.source_auth import (
    DOMAIN, GENESIS_HEAD, TRUST_SCHEMA, PROOF_SCHEMA, authenticate_and_evaluate,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 12, 3, 25, tzinfo=timezone.utc)


def pin(raw: bytes) -> str:
    return "sha256:" + sha256(raw).hexdigest()


def case():
    intent_bytes = (ROOT / "fixtures/intent.json").read_bytes()
    obs = json.loads((ROOT / "fixtures/clean.json").read_bytes())
    obs["source"] = "offline-pinned-benchmark-source"
    ob_bytes = canonical(obs)
    key = Ed25519PrivateKey.from_private_bytes(sha256(b"ral-benchmark-test-only-not-secret").digest())
    pub = base64.b64encode(key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    authority_bytes = canonical({"schema": TRUST_SCHEMA, "source_id": obs["source"],
        "key_id": "benchmark-test-only", "public_key_ed25519": pub, "workloads": ["lab/demo"]})
    payload = {"schema": PROOF_SCHEMA, "domain": DOMAIN, "source_id": obs["source"],
               "key_id": "benchmark-test-only", "sequence": 1, "prev_head": GENESIS_HEAD,
               "observation_sha256": pin(ob_bytes), "workload": obs["workload"],
               "observed_at": obs["observed_at"]}
    attestation = canonical({**payload,
        "signature": base64.b64encode(key.sign(canonical(payload))).decode()})
    return {"intent_bytes": intent_bytes, "observation_bytes": ob_bytes,
            "attestation_bytes": attestation, "authority_bytes": authority_bytes,
            "expected_intent_sha256": pin(intent_bytes),
            "expected_authority_sha256": pin(authority_bytes),
            "expected_sequence": 1, "expected_prev_head": GENESIS_HEAD, "now": NOW}


def bench(samples: int = 500) -> dict:
    if type(samples) is not int or samples < 1 or samples > 10_000:
        raise ValueError("samples must be in [1,10000]")
    args = case()
    durations = []
    tracemalloc.start()
    start_cpu = time.process_time_ns()
    for _ in range(samples):
        started = time.perf_counter_ns()
        result = authenticate_and_evaluate(**args)
        durations.append((time.perf_counter_ns()-started)/1000)
        assert result.source_authenticated and result.finding.status == "OK"
    cpu = (time.process_time_ns()-start_cpu)/1_000_000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    sorted_times = sorted(durations)
    def p(q):
        return round(sorted_times[min(len(sorted_times)-1,math.ceil(len(sorted_times)*q)-1)], 3)
    return {"scope": "preloaded, fixed synthetic key/source; independent pins are test assumptions; no real source authentication",
            "method": "sequential in-process full cryptographic gate with re-used test checkpoint; deliberately no durable advancement; NOT end-to-end detection latency",
            "samples": samples, "p50_us": p(.5), "p95_us": p(.95), "p99_us": p(.99),
            "cpu_ms": round(cpu,3), "traced_python_heap_peak_bytes": peak,
            "pod_cpu_rss_measured": False, "upstream_signature_verified": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=500)
    p.add_argument("--output", type=Path, default=Path("results/source_auth_benchmark.json"))
    args = p.parse_args()
    result = bench(args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
