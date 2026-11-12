"""Controlled synthetic observability study, NOT a comparison to upstream products.

Run from the repository root: python scripts/bench_incremental_value.py
The complete-input reference comparator is intentionally a separate implementation.
Parity means correlation alone is not evidence of algorithmic novelty.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import time
from typing import Literal

from runtime_assurance_lab.contracts import Intent, Observation
from runtime_assurance_lab.evaluate import evaluate, _evaluate_authenticated_claims, naive_baseline

UTC_NOW = datetime(2026, 11, 12, 3, 25, tzinfo=timezone.utc)
Truth = Literal["clean", "drift"]


def token(text: str) -> str:
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Case:
    scenario: str
    intent: Intent
    observation: Observation | None
    truth: Truth
    fully_observable: bool


def scenarios(seed: int = 0) -> list[Case]:
    """Independent synthetic truth labels; not inferred from evaluator outputs."""
    identifier = f"trial-{seed}"
    identity = f"lab/{identifier}"
    expected = Intent(identity, "hf://lab/approved", token("model"), token("image"), token("recipe"))
    valid = Observation(identity, expected.model_ref, expected.model_digest, expected.image_digest,
                        expected.platform_recipe_digest, UTC_NOW - timedelta(seconds=10), "verified",
                        f"fixture:{identifier}", "synthetic-source")
    changed = replace(valid, model_digest=token("different-model"))
    cases = [
        ("clean", valid, "clean", True),
        ("model_ref", replace(valid, model_ref="hf://lab/other"), "drift", True),
        ("model_digest", changed, "drift", True),
        ("image_digest", replace(valid, image_digest=token("other-image")), "drift", True),
        ("recipe_digest", replace(valid, platform_recipe_digest=token("other-recipe")), "drift", True),
        ("missing_clean", None, "clean", False),
        ("missing_hidden_drift", None, "drift", False),
        ("stale_clean", replace(valid, observed_at=UTC_NOW - timedelta(seconds=310)), "clean", False),
        ("stale_hidden_drift", replace(changed, observed_at=UTC_NOW - timedelta(seconds=310)), "drift", False),
        ("future_hidden_drift", replace(changed, observed_at=UTC_NOW + timedelta(seconds=60)), "drift", False),
        ("unverified_clean", replace(valid, model_confidence="declared"), "clean", False),
        ("unresolved_clean", replace(valid, model_digest=None), "clean", False),
    ]
    return [Case(name, expected, obs, truth, observable) for name, obs, truth, observable in cases]


def independent_complete_input_comparator(intent: Intent, obs: Observation | None, *, now: datetime) -> str:
    """Separate complete-input policy *reference*, not actual AICR or k8s-aibom.

    Uses the SAME inputs/capabilities as the system, so parity is expected.
    No signature or real source-provenance checking is provided by either.
    """
    if obs is None or obs.workload != intent.workload:
        return "UNKNOWN"
    if obs.observed_at > now + timedelta(seconds=30):
        return "UNKNOWN"
    if now - obs.observed_at > timedelta(seconds=300):
        return "STALE"
    if any(getattr(obs, name) is not None and getattr(obs, name) != getattr(intent, name)
           for name in ("model_ref", "model_digest", "image_digest", "platform_recipe_digest")):
        return "DRIFT"
    if any(getattr(obs, name) is None
           for name in ("model_ref", "model_digest", "image_digest", "platform_recipe_digest")):
        return "UNKNOWN"
    if obs.model_confidence != "verified":
        return "UNKNOWN"
    return "OK"


def _p95_micros(fn, rows: list[Case], rounds: int = 5) -> float:
    timings: list[float] = []
    for _ in range(rounds):
        for case in rows:
            start = time.perf_counter_ns()
            fn(case.intent, case.observation, now=UTC_NOW)
            timings.append((time.perf_counter_ns() - start) / 1000)
    timings.sort()
    return timings[min(len(timings)-1, math.ceil(len(timings)*0.95)-1)]


def study(trials: int = 50, *, measure_speed: bool = True) -> dict:
    if type(trials) is not int or not 1 <= trials <= 500:
        raise ValueError("trials must be an integer in [1,500]")
    rows = [case for n in range(trials) for case in scenarios(n)]
    counts = {"cases": len(rows), "trials": trials, "fully_observable": 0,
              "latent_drift": 0, "confirmed_drift": 0, "observable_drift": 0,
              "false_drift_on_clean": 0, "unsupported_ok": 0,
              "complete_input_reference_disagreements": 0, "naive_false_ok": 0}
    breakdown: dict[str, dict[str, object]] = {}
    for case in rows:
        verdict = _evaluate_authenticated_claims(case.intent, case.observation, now=UTC_NOW).status
        baseline = independent_complete_input_comparator(case.intent, case.observation, now=UTC_NOW)
        naive = naive_baseline(case.intent, case.observation, now=UTC_NOW).status
        entry = breakdown.setdefault(case.scenario, {"truth": case.truth, "fully_observable": case.fully_observable,
                                                      "outcomes": {}})
        entry["outcomes"][verdict] = entry["outcomes"].get(verdict, 0) + 1
        counts["fully_observable"] += int(case.fully_observable)
        counts["latent_drift"] += int(case.truth == "drift")
        counts["confirmed_drift"] += int(case.truth == "drift" and verdict == "DRIFT")
        counts["observable_drift"] += int(case.truth == "drift" and case.fully_observable)
        counts["false_drift_on_clean"] += int(case.truth == "clean" and verdict == "DRIFT")
        counts["unsupported_ok"] += int(not case.fully_observable and verdict == "OK")
        counts["complete_input_reference_disagreements"] += int(verdict != baseline)
        counts["naive_false_ok"] += int((case.truth == "drift" or not case.fully_observable) and naive == "OK")
    # Adversarial provenance probe *outside* the labeled matrix: an attacker
    # who can forge all source claims can assert a complete, matching, "verified"
    # observation while the hidden execution is different. No provenance input
    # exists in this policy contract, so matching claims yield an unsafe OK.
    example = scenarios(0)[0]
    spoofed_observation = example.observation
    assert spoofed_observation is not None
    spoofed_claim_status = evaluate(example.intent, spoofed_observation, now=UTC_NOW).status
    assert spoofed_claim_status == "UNKNOWN"  # fail-closed untrusted public entrypoint

    results = {
        "scope": "HISTORICAL CLAIM-ONLY deterministic synthetic negative controls; public evaluate() now fails closed; not actual NVIDIA/Google/Sigstore performance",
        "definition": "HISTORICAL CLAIM-ONLY policy comparison. DRIFT is a reported mismatch, NOT proof of malicious or executed runtime drift",
        "complete_claim_definition": "HISTORICAL CLAIM-ONLY comparator; fresh, complete synthetic claims with a verified label. NOT source-authenticated or model-execution evidence",
        "sample_limitation": "Trial repetitions change workload identifiers, not underlying conditions; this is NOT a statistically representative workload distribution",
        "timing_method": "five ordered rounds of preloaded same-process calls via perf_counter_ns, no traced heap; no file I/O, Kubernetes, or GPU",
        "truth_source": "predefined synthetic scenario construction (not a tool result)",
        "counts": counts,
        "metrics": {
            "overall_latent_drift_recall": counts["confirmed_drift"]/counts["latent_drift"],
            "observable_drift_recall": counts["confirmed_drift"]/counts["observable_drift"],
            "false_drift_rate_on_clean": counts["false_drift_on_clean"] / (len(rows)-counts["latent_drift"]),
            "unsupported_ok_rate": counts["unsupported_ok"] / (len(rows)-counts["fully_observable"]),
            "complete_input_reference_disagreement_rate": counts["complete_input_reference_disagreements"]/len(rows),
        },
        "source_forgery_probe": {
            "assumed_hidden_truth": "drift despite counterfeit complete matching observation",
            "reported_status": spoofed_claim_status,
            "unsafe_ok_possible_when_input_source_is_untrusted": False,
            "security_gate_passed": True,
            "root_cause": "original v1 policy trusted the caller-provided verified label; public evaluate now refuses unpinned untrusted sources",
        },
        "interpretation": {
            "upstream_tools_executed": False,
            "product_differentiation_proven": False,
            "negative_control": "Same-input independent reference matches; no incremental detection is established by this fixture study",
            "falsification_rule": "Stop claiming novelty if representative authorized upstream tool composition matches coverage and overhead",
        },
        "by_scenario": breakdown,
    }
    if measure_speed:
        results["local_preloaded_processing_p95_us"] = {
            "claim_only_comparator": _p95_micros(_evaluate_authenticated_claims, rows),
            "same_input_reference": _p95_micros(independent_complete_input_comparator, rows),
        }
    return results


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("results/incremental_value.json"))
    args = parser.parse_args()
    report = study(args.trials)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "metrics": report["metrics"],
                      "scope": report["scope"]}, sort_keys=True))


if __name__ == "__main__":
    main()
