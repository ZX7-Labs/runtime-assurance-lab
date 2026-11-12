"""Single-host processing microbenchmark for the synthetic AIBOM JSON adapter.

Does not include CR watch/poll, network, disk access, or Kubernetes resources.
"""
from __future__ import annotations
import json
from pathlib import Path
from statistics import quantiles, median
from time import perf_counter_ns, process_time_ns
import tracemalloc
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from runtime_assurance_lab.aibom_adapter import normalize_aibom

ROOT = Path(__file__).resolve().parents[1]
fixture = json.loads((ROOT / 'fixtures/aibom-v1beta1-synthetic.json').read_text())
loops = 1000
for _ in range(100):
    normalize_aibom(fixture)
tracemalloc.start()
start_cpu = process_time_ns()
samples = []
for _ in range(loops):
    start = perf_counter_ns()
    normalize_aibom(fixture)
    samples.append((perf_counter_ns() - start) / 1000)
cpu_ms = (process_time_ns() - start_cpu) / 1e6
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
report = {
    'scope': 'synthetic pre-parsed JSON adapter only; not cluster detection latency',
    'upstream_schema': 'k8s-aibom/v1.6.2 AIBOM/v1beta1',
    'loops': loops,
    'median_us': round(median(samples), 3),
    'p95_us': round(quantiles(samples, n=100)[94], 3),
    'max_us': round(max(samples), 3),
    'cpu_ms': round(cpu_ms, 3),
    'tracemalloc_peak_bytes': peak,
}
path = ROOT / 'results/aibom_adapter_benchmark.json'
path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(report, indent=2, sort_keys=True))
