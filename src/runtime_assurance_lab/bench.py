"""Fixed-seed synthetic classification and offline microbenchmarks.

These results are not a live Kubernetes, AICR, Sigstore or k8s-aibom comparison.
"""
from __future__ import annotations
from dataclasses import replace, asdict
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import math
import statistics
import time
import tracemalloc
from .contracts import Intent, Observation
from .evaluate import evaluate, naive_baseline
from .evidence import append, generate_signer, head, verify, verify_decision_semantics, canonical, sha

FIXED_NOW = datetime(2026, 11, 12, 3, 25, tzinfo=timezone.utc)
SCENARIOS = ("clean", "model_ref", "model_digest", "image_digest", "platform_recipe_digest",
             "stale", "missing", "unverified", "unresolved", "future")


def d(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def dataset(repetitions: int = 70):
    """Labels come from scenario creation, NOT from the tested evaluator."""
    for n in range(repetitions):
        for scenario in SCENARIOS:
            wid = f"lab/item-{n}-{scenario.replace('_','-')}"
            intent = Intent(wid, "hf://lab/approved", d("model"), d("image"), d("recipe"))
            ob = Observation(wid, "hf://lab/approved", d("model"), d("image"), d("recipe"),
                             FIXED_NOW - timedelta(seconds=10), "verified", "synthetic.status.ref", "synthetic-aibom")
            if scenario == "model_ref": ob = replace(ob, model_ref="hf://lab/different")
            if scenario == "model_digest": ob = replace(ob, model_digest=d("changed-model"))
            if scenario == "image_digest": ob = replace(ob, image_digest=d("changed-image"))
            if scenario == "platform_recipe_digest": ob = replace(ob, platform_recipe_digest=d("changed-recipe"))
            if scenario == "stale": ob = replace(ob, observed_at=FIXED_NOW - timedelta(seconds=301))
            if scenario == "missing": ob = None
            if scenario == "unverified": ob = replace(ob, model_confidence="declared")
            if scenario == "unresolved": ob = replace(ob, model_digest=None)
            if scenario == "future": ob = replace(ob, observed_at=FIXED_NOW + timedelta(seconds=31))
            yield intent, ob, scenario != "clean", scenario


def classification(rows, evaluator):
    tp = tn = fp = fn = 0
    by_scenario: dict[str, dict[str, int]] = {}
    for intent, obs, positive, scenario in rows:
        alert = evaluator(intent, obs, now=FIXED_NOW).status != "OK"
        entry = by_scenario.setdefault(scenario, {"total": 0, "alerts": 0})
        entry["total"] += 1
        entry["alerts"] += int(alert)
        if positive and alert: tp += 1
        elif positive and not alert: fn += 1
        elif not positive and alert: fp += 1
        else: tn += 1
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "recall": tp/(tp+fn) if (tp+fn) else None,
            "false_positive_rate": fp/(fp+tn) if (fp+tn) else None,
            "by_scenario": by_scenario}


def percentile(samples: list[float], p: float) -> float:
    ordered = sorted(samples)
    return ordered[min(len(ordered)-1, math.ceil(len(ordered)*p)-1)]


def microbench(rows, evaluator, loops: int = 5) -> dict:
    # Measurement excludes fixture generation and includes Python function calls.
    gc.collect()
    times: list[float] = []
    tracemalloc.start()
    start_cpu = time.process_time_ns()
    start_wall = time.perf_counter_ns()
    for _ in range(loops):
        for intent, obs, _, _ in rows:
            t = time.perf_counter_ns()
            evaluator(intent, obs, now=FIXED_NOW)
            times.append((time.perf_counter_ns()-t)/1000)
    wall_ms = (time.perf_counter_ns()-start_wall)/1e6
    cpu_ms = (time.process_time_ns()-start_cpu)/1e6
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"evaluations": len(times), "p50_us": percentile(times, .50),
            "p95_us": percentile(times, .95), "p99_us": percentile(times, .99),
            "wall_ms": wall_ms, "cpu_ms": cpu_ms, "python_heap_peak_bytes": peak}


def crypto_bench(events: int = 180):
    keys = {kind: generate_signer() for kind in ("intent", "observation", "decision")}
    trust = {kind: (keys[kind][1], kind) for kind in keys}
    log = []
    start = time.perf_counter_ns()
    for i in range(events):
        kind = "intent" if i % 3 == 0 else "observation" if i % 3 == 1 else "decision"
        refs = []
        if kind == "decision":
            refs = [sha(canonical(log[-2])), sha(canonical(log[-1]))]
        append(log, kind, {"workload": f"lab/fixture-{i//3}", "item": i},
               refs, kind, keys[kind][0])
    sign_ms = (time.perf_counter_ns()-start)/1e6
    digest_head = head(log)
    start = time.perf_counter_ns()
    result, reason = verify(log, trust, expected_head=digest_head, expected_count=events)
    verify_ms = (time.perf_counter_ns()-start)/1e6
    assert result, reason
    return {"events": events, "append_sign_ms": sign_ms, "verify_ms": verify_ms,
            "append_sign_per_event_us": sign_ms*1000/events,
            "verify_per_event_us": verify_ms*1000/events}


def pipeline_bench(repetitions: int = 5) -> dict:
    """In-process signed synthetic event-to-verdict latency, NO watch/network lag."""
    from .evaluate import POLICY_VERSION
    keys = {kind: generate_signer() for kind in ("intent", "observation", "decision")}
    trust = {kind: (keys[kind][1], kind) for kind in keys}
    samples: list[float] = []
    for intent, observation, _, case in dataset(repetitions):
        started = time.perf_counter_ns()
        events: list[dict] = []
        a = append(events, "intent", asdict(intent), [], "intent", keys["intent"][0])
        refs = [sha(canonical(a))]
        if observation is not None:
            ob = asdict(observation)
            ob["observed_at"] = observation.observed_at.isoformat()
            b = append(events, "observation", ob, [], "observation", keys["observation"][0])
            refs.append(sha(canonical(b)))
        finding = evaluate(intent, observation, now=FIXED_NOW).to_dict()
        append(events, "decision", {**finding, "policy_version": POLICY_VERSION,
               "evaluated_at": FIXED_NOW.isoformat()}, refs, "decision", keys["decision"][0])
        verified, reason = verify(events, trust, expected_head=head(events), expected_count=len(events))
        semantically_valid, semantic_reason = verify_decision_semantics(events, trusted_now=FIXED_NOW.isoformat())
        if not verified or not semantically_valid:
            raise AssertionError((case, reason, semantic_reason))
        samples.append((time.perf_counter_ns()-started)/1000)
    return {"events_processed": len(samples), "p50_us": percentile(samples, .5),
            "p95_us": percentile(samples, .95), "p99_us": percentile(samples, .99),
            "scope": "in-memory synthetic input through signing, evidence integrity check and semantic decision verification; excludes collection/polling/network/disk"}


def run(repetitions: int = 70, loops: int = 5) -> dict:
    rows = list(dataset(repetitions))
    # Benchmark order is documented; run an opposite-order replicate for regression follow-up.
    naive = microbench(rows, naive_baseline, loops)
    proposed = microbench(rows, evaluate, loops)
    c1 = classification(rows, naive_baseline)
    c2 = classification(rows, evaluate)
    return {"experiment": "offline-synthetic-v1", "fixed_now": FIXED_NOW.isoformat(),
            "sample_size": len(rows), "class_balance": {"clean": repetitions, "needs_attention": len(rows)-repetitions},
            "definitions": {"positive": "intentionally mutated or unverified scenario; UNKNOWN/STALE/DRIFT all count as needs-attention",
                            "false_positive": "an alert on a constructed fully verified and fresh clean case",
                            "latency": "per-evaluation Python microseconds, not event-to-detection or cluster latency",
                            "cpu": "process CPU time in an in-process Python microbenchmark",
                            "memory": "peak traced Python heap allocations; not pod RSS or cluster overhead"},
            "naive_local_comparator": {"classification": c1, "microbench": naive},
            "proposed": {"classification": c2, "microbench": proposed},
            "crypto": crypto_bench(),
            "synthetic_event_to_verdict": pipeline_bench(),
            "upstream_live_comparison_executed": False}
