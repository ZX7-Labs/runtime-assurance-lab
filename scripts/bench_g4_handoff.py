"""Reproducible *synthetic preloaded processing* baseline for G4 handoff checks.

NOT an upstream comparison, real end-to-end latency, trust verification or SLO.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter_ns, process_time_ns
import tracemalloc

from runtime_assurance_lab.g4_handoff import inspect_handoff

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 10 <= args.samples <= 10000:
        parser.error("samples must be between 10 and 10000")
    sources = {
        "intent": (ROOT / "fixtures/intent-aicr-synthetic.json").read_bytes(),
        "recipe": (ROOT / "fixtures/aicr-recipe-result-synthetic.json").read_bytes(),
        "aibom": (ROOT / "fixtures/aibom-v1beta1-synthetic.json").read_bytes(),
    }
    inputs = {
        **{f"{name}_bytes": raw for name, raw in sources.items()},
        **{f"expected_{name}_sha256": "sha256:" + sha256(raw).hexdigest()
           for name, raw in sources.items()},
    }
    for _ in range(10):
        inspect_handoff(**inputs)
    tracemalloc.start()
    process_start = process_time_ns()
    durations = []
    for _ in range(args.samples):
        start = perf_counter_ns()
        result = inspect_handoff(**inputs)
        durations.append((perf_counter_ns() - start) / 1000)
        if result["g4_authorized"] or result["decision"] != "PAUSE_PRODUCT_BUILD":
            raise RuntimeError("UNSAFE_GO result in benchmark")
    cpu_ms = (process_time_ns() - process_start) / 1e6
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    summary = {
        "scope": "preloaded synthetic JSON + byte-pin/schema checks only; excludes file IO, upstream proof, cluster, GPU and trusted custody",
        "count": args.samples,
        "p50_us": round(median(durations), 3),
        "p95_us": round(quantiles(durations, n=100)[94], 3),
        "max_us": round(max(durations), 3),
        "process_cpu_total_ms": round(cpu_ms, 3),
        "peak_traced_python_heap_bytes": peak,
        "g4_authorized": False,
        "decision": "PAUSE_PRODUCT_BUILD",
    }
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(summary, sort_keys=True))
    return 0  # benchmark completion, not product GO


if __name__ == "__main__":
    raise SystemExit(main())
