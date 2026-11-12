"""Reproducible local-only preloaded AICR RecipeResult hash/parse baseline.

Not cluster detection latency, production SLO or an upstream AICR benchmark.
"""
from pathlib import Path
import json
from statistics import median, quantiles
from time import perf_counter_ns, process_time_ns
import tracemalloc
from runtime_assurance_lab.aicr_adapter import pin_recipe
from runtime_assurance_lab.contracts import Intent

ROOT = Path(__file__).resolve().parents[1]
raw = (ROOT/'fixtures/aicr-recipe-result-synthetic.json').read_bytes()
intent = Intent.parse(json.loads((ROOT/'fixtures/intent-aicr-synthetic.json').read_text()))
tracemalloc.start()
start_cpu = process_time_ns()
samples = []
for _ in range(1000):
    t = perf_counter_ns()
    result = pin_recipe(raw, intent.platform_recipe_digest, intent)
    samples.append((perf_counter_ns() - t) / 1e3)
assert result.sha256 == intent.platform_recipe_digest
cpu_ms = (process_time_ns() - start_cpu) / 1e6
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
data = {
    'scope': '1000 preloaded synthetic RecipeResult byte-pin+JSON conversions; no file IO, auth, cluster or GPU',
    'samples': 1000,
    'median_us': round(median(samples), 3),
    'p95_us': round(quantiles(samples, n=100)[94], 3),
    'max_us': round(max(samples), 3),
    'cpu_ms_total': round(cpu_ms, 3),
    'peak_traced_python_heap_bytes': peak,
}
print(json.dumps(data, indent=2, sort_keys=True))
