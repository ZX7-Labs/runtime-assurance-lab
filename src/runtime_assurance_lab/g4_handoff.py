"""Untrusted, read-only G4 operator evidence handoff preflight.

This verifies *input integrity against caller-provided SHA256 pins and schema
compatibility*, not upstream signature/issuer identity, cluster state or
execution. It intentionally cannot return authenticated OK or product GO.
It does not collect, persist, print, or upload source payloads.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from .aibom_adapter import normalize_aibom
from .aicr_adapter import pin_recipe
from .contracts import Intent, digest
from .json_strict import loads_strict

SCHEMA = "ral-g4-untrusted-handoff/v1"
MAX_RAW_BYTES = 8 * 1024 * 1024
REQUIRED_SOURCES = ("intent", "recipe", "aibom")
MISSING_INDEPENDENT_CONTROLS = (
    "AUTHENTIC_UPSTREAM_SIGNATURE_AND_CREATOR_IDENTITY_VERIFICATION",
    "INDEPENDENT_INTENT_AND_TRUST_ROOT_CUSTODY",
    "DURABLE_INDEPENDENT_MONOTONIC_CHECKPOINT_AND_TRUSTED_CLOCK",
    "ACTUAL_SAME_WORKLOAD_CROSS_PLANE_BINDING_AND_EXECUTION_WITNESS",
    "BLINDED_EQUAL_INPUT_UPSTREAM_BASELINE_AND_CUSTOMER_VALIDATION",
)


def _read_source(raw: bytes, name: str, expected: str) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RAW_BYTES:
        raise ValueError(f"{name}: invalid input bytes")
    digest(expected, required=True)
    if expected != "sha256:" + sha256(raw).hexdigest():
        raise ValueError(f"{name}: external byte pin mismatch")
    try:
        parsed = loads_strict(raw)
    except (UnicodeDecodeError, RecursionError) as exc:
        raise ValueError(f"{name}: invalid strict JSON") from exc
    if type(parsed) is not dict:
        raise ValueError(f"{name}: expected object")
    return parsed


def inspect_handoff(*, intent_bytes: bytes, recipe_bytes: bytes, aibom_bytes: bytes,
                    expected_intent_sha256: str, expected_recipe_sha256: str,
                    expected_aibom_sha256: str) -> dict[str, Any]:
    """Review raw operator-supplied artifacts without upgrading source trust.

    All three pins must be supplied OUT OF BAND by the operator. Even if
    verified, they prove only equality to that pin. No self-attested trust
    status in any input can unlock an authenticated positive verdict.
    The returned report contains no raw workloads, model names or source text.
    """
    intent_json = _read_source(intent_bytes, "intent", expected_intent_sha256)
    _read_source(recipe_bytes, "recipe", expected_recipe_sha256)
    aibom_json = _read_source(aibom_bytes, "aibom", expected_aibom_sha256)
    intent = Intent.parse(intent_json)
    # Parsed twice on purpose: pin_recipe is the separately tested AICR
    # version-pinned boundary. This also checks the recipe against intent.
    recipe = pin_recipe(recipe_bytes, expected_recipe_sha256, intent)
    aibom = normalize_aibom(aibom_json)

    # An AICR RecipeResult itself lacks a runtime workload identity. A
    # matching intent and AIBOM workload is only a structural assertion,
    # NOT a cryptographically verified AICR-to-workload linkage.
    if aibom.observation is None:
        state = "BLOCKED_INCOMPLETE_AIBOM"
    elif aibom.observation.workload != intent.workload:
        state = "BLOCKED_WORKLOAD_IDENTITY_CONFLICT"
    elif aibom.observation.model_ref is None:
        state = "BLOCKED_MODEL_IDENTITY_UNRESOLVED"
    elif aibom.observation.model_ref != intent.model_ref:
        state = "BLOCKED_MODEL_CLAIM_CONFLICT"
    else:
        summary = aibom_json.get("status", {}).get("summary", {})
        workload_summary = summary.get("workload", {}) if isinstance(summary, dict) else {}
        category = workload_summary.get("category") if isinstance(workload_summary, dict) else None
        if (recipe.intent_category not in (None, "any") and category is not None and
                recipe.intent_category != category):
            state = "BLOCKED_WORKLOAD_CATEGORY_CONFLICT"
        else:
            state = "STRUCTURALLY_COMPATIBLE_UNAUTHENTICATED"
    return {
        "schema": SCHEMA,
        "decision": "PAUSE_PRODUCT_BUILD",
        "handoff_state": state,
        "artifact_byte_pins_match": True,
        "pins_established_independently": False,
        "authentic_upstream_provenance_verified": False,
        "cross_plane_runtime_binding_verified": False,
        "runtime_model_execution_attested": False,
        "g4_authorized": False,
        "source_type": "OPERATOR_SUPPLIED_UNTRUSTED_EXPORTS",
        "sources": {k: {"sha256": v, "bytes": len(raw)} for k, v, raw in (
            ("intent", expected_intent_sha256, intent_bytes),
            ("aicr_recipe", expected_recipe_sha256, recipe_bytes),
            ("aibom", expected_aibom_sha256, aibom_bytes),
        )},
        "aicr": {"source_version": recipe.source_version,
                 "component_count": len(recipe.component_names),
                 "category": recipe.intent_category,
                 "limitations": list(recipe.limitations)},
        "aibom": {"source_version": aibom.source_version,
                  "observation_available": aibom.observation is not None,
                  "limitations": list(aibom.limitations)},
        "missing_independent_controls": list(MISSING_INDEPENDENT_CONTROLS),
    }
