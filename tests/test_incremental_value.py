"""Negative controls for synthetic claims; real tool differentiation remains untested."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest
from runtime_assurance_lab.contracts import Observation
from runtime_assurance_lab.evaluate import evaluate

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bench_incremental_value.py"
spec = importlib.util.spec_from_file_location("bench_incremental_value", SCRIPT)
assert spec and spec.loader
# Import as a normal module for dataclass annotation resolution.
import sys
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_synthetic_negative_controls_expose_coverage_not_novelty():
    report = module.study(3, measure_speed=False)
    n = report["counts"]
    assert n["cases"] == 36
    assert n["complete_input_reference_disagreements"] == 0
    assert n["unsupported_ok"] == 0
    assert n["false_drift_on_clean"] == 0
    assert report["metrics"]["observable_drift_recall"] == 1.0
    assert 0 < report["metrics"]["overall_latent_drift_recall"] < 1
    assert n["naive_false_ok"] > 0
    assert report["interpretation"]["product_differentiation_proven"] is False
    assert report["source_forgery_probe"]["unsafe_ok_possible_when_input_source_is_untrusted"]
    assert report["source_forgery_probe"]["reported_status"] == "OK"
    assert report["source_forgery_probe"]["security_gate_passed"] is False


def test_freshness_masks_hidden_drift_and_returns_needs_review():
    for name in ("stale_hidden_drift", "future_hidden_drift", "missing_hidden_drift"):
        case = next(c for c in module.scenarios() if c.scenario == name)
        assert not case.fully_observable and case.truth == "drift"
        status = evaluate(case.intent, case.observation, now=module.UTC_NOW).status
        assert status in {"UNKNOWN", "STALE"}
        assert status != "DRIFT"


def test_independent_comparator_mismatches_are_exposed(monkeypatch):
    monkeypatch.setattr(module, "independent_complete_input_comparator", lambda *a, **k: "OK")
    counts = module.study(2, measure_speed=False)["counts"]
    assert counts["complete_input_reference_disagreements"] > 0


@pytest.mark.parametrize("bad", [0, -1, 501, True, 2.3, "5"])
def test_trial_bounds(bad):
    with pytest.raises(ValueError):
        module.study(bad, measure_speed=False)
