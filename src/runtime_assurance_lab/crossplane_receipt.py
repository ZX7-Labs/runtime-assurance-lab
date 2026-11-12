"""Replayable, bounded offline correlation receipt (NOT a trusted attestation).

The caller MUST obtain the recipe pin, intent, AIBOM and clock through separately
appropriate trust channels. This module proves only deterministic *replay*
against the exact bytes it was given; it does not sign, anchor or authenticate
upstream evidence, and does not prove live model execution.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from .aicr_adapter import MAX_RECIPE_BYTES, pin_recipe
from .aibom_adapter import normalize_aibom
from .contracts import Intent, timestamp
from .evaluate import POLICY_VERSION, evaluate
from .evidence import canonical
from .json_strict import loads_strict

SCHEMA = "ral-offline-crossplane-receipt/v1"
MAX_SOURCE_BYTES = 8 * 1024 * 1024
LIMITATIONS = (
    "AICR_PIN_AND_INTENT_NOT_SOURCE_AUTHENTICATED",
    "AIBOM_CR_NOT_SOURCE_AUTHENTICATED",
    "MODEL_EXECUTION_NOT_ATTESTED",
    "RECEIPT_NOT_SIGNED_OR_EXTERNALLY_ANCHORED",
)


def _parse(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise ValueError(f"{label} must be bounded nonempty bytes")
    try:
        value = loads_strict(raw)
    except (UnicodeDecodeError, RecursionError) as exc:
        raise ValueError(f"{label} is not valid strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be JSON object")
    return value


def _sha(raw: bytes) -> str:
    return "sha256:" + sha256(raw).hexdigest()


def make_receipt(*, intent_bytes: bytes, recipe_bytes: bytes, aibom_bytes: bytes,
                 expected_recipe_sha256: str, trusted_now: str) -> dict[str, Any]:
    """Build an exactly replayable report from three untrusted local source files.

    No silent upgrades from source self-consistency to attested runtime truth.
    """
    intent = Intent.parse(_parse(intent_bytes, "intent"))
    if not isinstance(recipe_bytes, bytes) or not 0 < len(recipe_bytes) <= MAX_RECIPE_BYTES:
        raise ValueError("recipe must be bounded nonempty bytes")
    recipe = pin_recipe(recipe_bytes, expected_recipe_sha256, intent)
    aibom = normalize_aibom(_parse(aibom_bytes, "AIBOM"))
    when = timestamp(trusted_now)
    result = evaluate(intent, aibom.observation, now=when)
    return {
        "schema": SCHEMA,
        "policy_version": POLICY_VERSION,
        "evaluated_at": when.isoformat(),
        "external_recipe_pin": expected_recipe_sha256,
        "input_sha256": {
            "intent": _sha(intent_bytes),
            "aicr_recipe": _sha(recipe_bytes),
            "aibom": _sha(aibom_bytes),
        },
        "decision": result.to_dict(),
        "adapters": {
            "aicr": {"source_version": recipe.source_version,
                     "component_count": len(recipe.component_names),
                     "limitations": list(recipe.limitations)},
            "aibom": {"source_version": aibom.source_version,
                      "limitations": list(aibom.limitations)},
        },
        "limitations": list(LIMITATIONS),
    }


def replay_receipt(receipt: Any, *, intent_bytes: bytes, recipe_bytes: bytes,
                   aibom_bytes: bytes, expected_recipe_sha256: str,
                   trusted_now: str) -> tuple[bool, str]:
    """Recompute from caller-supplied sources and external pin/time, never report claims.

    Any modified status, omitted limitation, altered digest, policy/clock or
    unknown field fails exact equality. This is **not** signature verification.
    """
    if not isinstance(receipt, dict):
        return False, "INVALID_RECEIPT_SHAPE"
    try:
        expected = make_receipt(intent_bytes=intent_bytes, recipe_bytes=recipe_bytes,
                                aibom_bytes=aibom_bytes,
                                expected_recipe_sha256=expected_recipe_sha256,
                                trusted_now=trusted_now)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return False, "SOURCE_OR_PIN_INVALID"
    # Python dict equality considers True == 1 and 1.0 == 1. Recheck the
    # canonical JSON *representation*, preserving JSON types, not Python ==.
    try:
        same = canonical(receipt) == canonical(expected)
    except (TypeError, ValueError, UnicodeError, RecursionError):
        same = False
    if not same:
        return False, "RECEIPT_CONTRADICTS_RAW_SOURCES"
    return True, "RAW_SOURCES_AND_DECISION_RECOMPUTED"
