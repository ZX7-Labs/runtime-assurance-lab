"""A fail-closed *research investment* gate, not a runtime assurance gate.

All evidence in this checkpoint is public upstream documentation plus existing
synthetic experiments. No user-editable evidence field is a proof of product value.
The only defensible outcome is to pause feature expansion pending independent G4.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .json_strict import loads_strict

SCHEMA = "ral-research-investment-v1"
DECISION = "PAUSE_PRODUCT_BUILD"
REQUIRED_PRODUCTS = frozenset({"NVIDIA_AICR", "GOOGLE_K8S_AIBOM", "SIGSTORE_POLICY"})
REQUIRED_GATES = ("authentic_upstream_evidence", "independently_anchored_provenance",
                  "representative_baseline_comparison", "customer_value_validation")
MAX_BYTES = 512 * 1024


def _read(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError("research evidence exceeds file bound")
    value = loads_strict(raw)
    if type(value) is not dict:
        raise ValueError("research evidence must be an object")
    return value


def _verified_matrix(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    if matrix.get("schema") != SCHEMA:
        raise ValueError("unsupported research schema")
    sources = matrix.get("sources")
    if type(sources) is not list or len(sources) != len(REQUIRED_PRODUCTS):
        raise ValueError("research matrix requires all three upstream providers")
    seen: set[str] = set()
    checked: list[dict[str, Any]] = []
    for record in sources:
        if type(record) is not dict:
            raise ValueError("source record must be an object")
        name = record.get("id")
        if type(name) is not str or name not in REQUIRED_PRODUCTS or name in seen:
            raise ValueError("duplicate, unknown or omitted source")
        seen.add(name)
        if type(record.get("capabilities")) is not list or not record["capabilities"]:
            raise ValueError("upstream capabilities missing")
        if any(type(x) is not str or not x.strip() for x in record["capabilities"]):
            raise ValueError("invalid upstream capability")
        url = record.get("reference")
        if type(url) is not str or not url.startswith("https://") or " " in url:
            raise ValueError("missing upstream source reference")
        pinned = record.get("reviewed_ref")
        if type(pinned) is not str or not pinned:
            raise ValueError("unidentified upstream release")
        checked.append(record)
    if seen != REQUIRED_PRODUCTS:
        raise ValueError("incomplete upstream coverage")
    claims = matrix.get("candidate_hypotheses")
    if type(claims) is not list or not claims or any(type(c) is not dict for c in claims):
        raise ValueError("falsifiable hypothesis list required")
    ids = [c.get("id") for c in claims]
    if any(type(i) is not str or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("invalid hypothesis IDs")
    for c in claims:
        if c.get("state") != "UNPROVEN" or type(c.get("falsifier")) is not str or not c["falsifier"]:
            raise ValueError("hypotheses must remain unproven until G4")
    return checked


def build_report(matrix: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    """Enforce NO-GO from documentation + historical same-input negative controls.

    No amount of caller-provided 'approved=true' creates authenticity or market
    validation. Independent G4 evidence must follow a future explicit review.
    """
    sources = _verified_matrix(matrix)
    counts = comparison.get("counts")
    interpretation = comparison.get("interpretation")
    scope = comparison.get("scope")
    probe = comparison.get("source_forgery_probe")
    if type(counts) is not dict or type(interpretation) is not dict or type(probe) is not dict:
        raise ValueError("missing historical negative-control results")
    if (type(counts.get("cases")) is not int or counts["cases"] <= 0 or
        type(counts.get("complete_input_reference_disagreements")) is not int or
        counts["complete_input_reference_disagreements"] < 0 or
        type(counts.get("fully_observable")) is not int or counts["fully_observable"] < 0):
        raise ValueError("invalid negative-control counts")
    if counts["complete_input_reference_disagreements"] > counts["cases"]:
        raise ValueError("invalid comparator disagreement count")
    if (interpretation.get("upstream_tools_executed") is not False or
        interpretation.get("product_differentiation_proven") is not False or
        type(scope) is not str or "CLAIM-ONLY" not in scope.upper()):
        raise ValueError("this gate accepts only the recorded historical claim-only experiment")
    if probe.get("reported_status") != "UNKNOWN" or probe.get("security_gate_passed") is not True:
        raise ValueError("post-M6 untrusted source regression is not verified")

    reference_disagreements = counts["complete_input_reference_disagreements"]
    missing = list(REQUIRED_GATES)
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "decision_is_production_approval": False,
        "reason": "UPSTREAM_OVERLAP_AND_INCREMENTAL_VALUE_UNPROVEN",
        "upstream_documented_capabilities": {x["id"]: x["capabilities"] for x in sorted(sources, key=lambda x: x["id"])},
        "experiment": {
            "cases": counts["cases"],
            "same_input_reference_disagreements": reference_disagreements,
            "scope": "HISTORICAL_CLAIM_ONLY_SYNTHETIC",
            "upstream_binaries_executed": False,
            "untrusted_source_post_gate": probe["reported_status"],
        },
        "candidate_hypotheses": [{"id": c["id"], "state": c["state"], "falsifier": c["falsifier"]}
                                 for c in matrix["candidate_hypotheses"]],
        "missing_independent_gates": missing,
        "next_action": "Obtain independently authenticated AICR/AIBOM evidence and authorized read-only "
                       "cluster baseline; compare existing upstream composition before any product expansion.",
        "limitations": [
            "This gate reviews official source documentation, not executed upstream tools.",
            "A signed upstream assertion is not physical GPU execution attestation.",
            "The same-input synthetic comparator cannot establish product differentiation.",
            "User-controlled inputs cannot establish independent trust or customer demand.",
        ],
    }


def run(matrix_path: Path, comparison_path: Path) -> dict[str, Any]:
    return build_report(_read(matrix_path), _read(comparison_path))
