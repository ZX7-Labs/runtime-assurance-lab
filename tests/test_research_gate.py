"""Executable stop/go negative controls, without pretending to validate customers."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from runtime_assurance_lab.research_gate import DECISION, build_report, run

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def records():
    matrix = json.loads((ROOT / "research/upstream_overlap.json").read_text())
    comparison = json.loads((ROOT / "results/incremental_value_post_gate.json").read_text())
    return matrix, comparison


def test_current_research_stops_new_product_features(records):
    matrix, control = records
    outcome = build_report(matrix, control)
    assert outcome["decision"] == "PAUSE_PRODUCT_BUILD"
    assert outcome["decision_is_production_approval"] is False
    assert outcome["experiment"]["upstream_binaries_executed"] is False
    assert outcome["experiment"]["same_input_reference_disagreements"] == 0
    assert set(outcome["upstream_documented_capabilities"]) == {
        "NVIDIA_AICR", "GOOGLE_K8S_AIBOM", "SIGSTORE_POLICY"}
    assert len(outcome["missing_independent_gates"]) == 4
    assert len(outcome["candidate_hypotheses"]) == 3


def test_real_files_same_result(records):
    assert run(ROOT / "research/upstream_overlap.json", ROOT / "results/incremental_value_post_gate.json") == build_report(*records)


@pytest.mark.parametrize("mutation", [
    lambda m: m.pop("sources"),
    lambda m: m["sources"].pop(),
    lambda m: m["sources"].append(deepcopy(m["sources"][0])),
    lambda m: m["sources"][0].update(reference="not a URL"),
    lambda m: m["sources"][0].update(capabilities=[]),
    lambda m: m["candidate_hypotheses"][0].update(state="PROVEN"),
    lambda m: m["candidate_hypotheses"][0].update(falsifier=""),
    lambda m: m["candidate_hypotheses"].append(deepcopy(m["candidate_hypotheses"][0])),
])
def test_unjustified_upstream_or_product_claim_fails(records, mutation):
    matrix, control = records
    mutation(matrix)
    with pytest.raises(ValueError):
        build_report(matrix, control)


@pytest.mark.parametrize("mutation", [
    lambda c: c["interpretation"].update(upstream_tools_executed=True),
    lambda c: c["interpretation"].update(product_differentiation_proven=True),
    lambda c: c.update(scope="LIVE_INTEGRATION_VALIDATED"),
    lambda c: c["counts"].update(cases=0),
    lambda c: c["counts"].update(complete_input_reference_disagreements=601),
    lambda c: c["source_forgery_probe"].update(reported_status="OK"),
    lambda c: c["source_forgery_probe"].update(security_gate_passed=False),
])
def test_claim_only_cannot_be_promoted_to_product_proof(records, mutation):
    matrix, control = records
    mutation(control)
    with pytest.raises(ValueError):
        build_report(matrix, control)


def test_forged_recorded_report_is_rejected(tmp_path):
    report = build_report(*(
        json.loads((ROOT / "research/upstream_overlap.json").read_text()),
        json.loads((ROOT / "results/incremental_value_post_gate.json").read_text()),
    ))
    report["decision"] = "GO_TO_PRODUCTION"
    wrong = tmp_path / "forged-report.json"
    wrong.write_text(json.dumps(report))
    cmd = [sys.executable, str(ROOT / "scripts/run_research_gate.py"), "--verify-report", str(wrong)]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 3
    assert json.loads(res.stdout)["decision"] == "INVALID_EVIDENCE"


def test_missing_report_rejected(tmp_path):
    cmd = [sys.executable, str(ROOT / "scripts/run_research_gate.py"), "--verify-report", str(tmp_path / "missing")]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 3
    assert json.loads(res.stdout)["decision"] == "INVALID_EVIDENCE"


def test_cli_refuses_report_overwrite(tmp_path):
    cmd = [sys.executable, str(ROOT / "scripts/run_research_gate.py"), "--output", str(tmp_path / "report.json")]
    assert subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).returncode == 0
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 3
    assert json.loads(result.stdout)["decision"] == "INVALID_EVIDENCE"


def test_research_report_rejects_duplicate_json_fields(tmp_path):
    source = tmp_path / "duplicate.json"
    source.write_text('{"decision": "PAUSE_PRODUCT_BUILD", "decision": "GO_TO_PRODUCTION"}')
    result = subprocess.run([sys.executable, str(ROOT / "scripts/run_research_gate.py"),
                             "--verify-report", str(source)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 3
    assert json.loads(result.stdout)["decision"] == "INVALID_EVIDENCE"


def test_research_report_rejects_oversized_file(tmp_path):
    source = tmp_path / "large.json"
    source.write_bytes(b"{" + b" " * (600 * 1024) + b"}")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/run_research_gate.py"),
                             "--verify-report", str(source)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 3
    assert json.loads(result.stdout)["decision"] == "INVALID_EVIDENCE"


def test_injected_go_flag_never_converts_synthetic_study_to_value_proof(records):
    matrix, comparison = records
    matrix["product_go"] = True
    comparison["market_demand_proven"] = True
    outcome = build_report(matrix, comparison)
    assert outcome["decision"] == DECISION
    assert outcome["decision_is_production_approval"] is False
