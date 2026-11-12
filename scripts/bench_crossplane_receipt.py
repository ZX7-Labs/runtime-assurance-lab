"""Preloaded synthetic receipt creation/replay overhead only. Not detection latency."""
from __future__ import annotations
import json
from pathlib import Path
from statistics import median
from time import perf_counter_ns, process_time_ns
import tracemalloc

from runtime_assurance_lab.crossplane_receipt import make_receipt, replay_receipt

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
SOURCES = {
    "intent_bytes": (FIX / "intent-aicr-synthetic.json").read_bytes(),
    "recipe_bytes": (FIX / "aicr-recipe-result-synthetic.json").read_bytes(),
    "aibom_bytes": (FIX / "aibom-v1beta1-synthetic.json").read_bytes(),
    "trusted_now": "2026-11-12T03:25:00Z",
}
SOURCES["expected_recipe_sha256"] = json.loads(SOURCES["intent_bytes"])["platform_recipe_digest"]
COUNT = 1000


def main():
    receipt = make_receipt(**SOURCES)
    measurements = {"create": [], "replay": []}
    tracemalloc.start()
    before_cpu = process_time_ns()
    for _ in range(COUNT):
        start = perf_counter_ns()
        a = make_receipt(**SOURCES)
        measurements["create"].append((perf_counter_ns() - start) / 1000)
        start = perf_counter_ns()
        ok, reason = replay_receipt(receipt, **SOURCES)
        measurements["replay"].append((perf_counter_ns() - start) / 1000)
        if not ok or a != receipt:
            raise AssertionError(reason)
    cpu_ms = (process_time_ns() - before_cpu) / 1e6
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    results = {"dataset": "preloaded synthetic sources, 1000 iterations each; no Kubernetes, IO, signatures or real latency",
               "iterations": COUNT, "cpu_total_ms": cpu_ms, "python_tracemalloc_peak_bytes": peak}
    for k, values in measurements.items():
        ordered = sorted(values)
        results[k] = {"median_us": round(median(values), 3),
                      "p95_us": round(ordered[int(COUNT * 0.95) - 1], 3),
                      "max_us": round(max(values), 3)}
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
