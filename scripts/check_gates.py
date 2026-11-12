"""Provisional empirical gate: synthetic-only, not a production SLA."""
import json
from pathlib import Path

report=json.loads(Path('results/benchmark.json').read_text())
p=report['proposed']
b=report['naive_local_comparator']
pc=p['classification']
pm=p['microbench']
bm=b['microbench']
checks={
    'synthetic_recall_ge_98pct':pc['recall']>=0.98,
    'synthetic_fpr_le_1pct':pc['false_positive_rate']<=0.01,
    'evaluation_p95_under_1ms':pm['p95_us']<=1000,
    'evaluation_p95_under_20x_naive':pm['p95_us']<=20*bm['p95_us'],
    'python_heap_peak_bounded':pm['python_heap_peak_bytes']<=2*bm['python_heap_peak_bytes']+1048576,
    'signed_pipeline_p95_under_10ms':report['synthetic_event_to_verdict']['p95_us']<=10000,
    'crypto_verification_measured':report['crypto']['verify_ms']>0,
}
output={'scope':'pilot synthetic-only acceptance thresholds, not release gate',
        'baseline_p95_us':bm['p95_us'],'proposed_p95_us':pm['p95_us'],
        'checks':checks,'passed':all(checks.values())}
Path('results/acceptance.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
print(json.dumps(output,indent=2,sort_keys=True))
raise SystemExit(0 if output['passed'] else 2)
