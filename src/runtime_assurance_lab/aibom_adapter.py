"""Read-only offline bridge for k8s-aibom v1.6.2 AIBOM/v1beta1.

Schema reference (Apache-2.0, no copied code):
https://github.com/GoogleCloudPlatform/k8s-aibom/blob/v1.6.2/api/v1beta1/aibom_types.go

An AIBOM Custom Resource is an inventory *claim*, not a signed runtime
attestation. This adapter deliberately cannot upgrade it to 'verified'.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .contracts import Observation, timestamp, string, workload
from .json_strict import loads_strict

API_VERSION = "aibom.k8saibom.dev/v1beta1"
SOURCE_VERSION = "k8s-aibom/v1.6.2"
MAX_INLINE_BOM_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class AdaptedAIBOM:
    observation: Observation | None
    limitations: tuple[str, ...]
    source_version: str = SOURCE_VERSION


def _object(value: Any, field: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _matching_coordinates(summary: dict, ref: dict, namespace: str) -> None:
    for key in ("apiVersion", "kind", "name"):
        if string(ref.get(key), f"spec.workloadRef.{key}") != string(summary.get(key), f"summary.workload.{key}"):
            raise ValueError("workload coordinates disagree across AIBOM fields")
    if string(summary.get("namespace"), "summary.workload.namespace") != namespace:
        raise ValueError("summary namespace disagrees with AIBOM namespace")


def _check_inline_document(status: dict) -> list[str]:
    """Check local bytes if present. A digest match is integrity, NOT authenticity."""
    document = status.get("bomDocument")
    if document is None:
        return ["BOM_DOCUMENT_MISSING"]
    document = _object(document, "status.bomDocument")
    if document.get("format") != "CycloneDX" or document.get("specVersion") != "1.6":
        raise ValueError("unsupported BOM format")
    digest = document.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid BOM sha256")
    if status.get("bomHash") and status["bomHash"] != digest:
        raise ValueError("bomHash differs from bomDocument.sha256")
    modes = ("inline" in document, "external" in document, document.get("truncated") is True)
    if sum(modes) != 1:
        raise ValueError("BOM must declare exactly one storage mode")
    if modes[0]:
        data = _object(document["inline"], "bomDocument.inline").get("data")
        if not isinstance(data, str) or len(data) > (MAX_INLINE_BOM_BYTES + 2) * 2:
            raise ValueError("invalid or oversized inline BOM encoding")
        try:
            raw = base64.b64decode(data, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("invalid inline BOM base64") from exc
        if len(raw) > MAX_INLINE_BOM_BYTES or sha256(raw).hexdigest() != digest:
            raise ValueError("inline BOM exceeds size limit or hash mismatch")
        try:
            bom = loads_strict(raw)
        except (UnicodeDecodeError, RecursionError) as exc:
            raise ValueError("inline BOM is not valid strict UTF-8 JSON") from exc
        if not isinstance(bom, dict) or bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
            raise ValueError("inline BOM document is not supported CycloneDX 1.6")
        if type(document.get("size")) is not int or document["size"] != len(raw):
            raise ValueError("inline BOM size mismatch")
        return ["INLINE_BOM_HASH_MATCHES_UNTRUSTED_CR"]
    if modes[1]:
        external = _object(document["external"], "bomDocument.external")
        if not isinstance(external.get("sink"), str) or not external["sink"]:
            raise ValueError("external BOM sink missing")
        # Never fetch external URLs or trust write-only sinks.
        return ["EXTERNAL_BOM_NOT_RETRIEVED"]
    return ["BOM_TRUNCATED"]


def normalize_aibom(resource: Any) -> AdaptedAIBOM:
    """Transform a pinned, untrusted CR into *partial* normalized evidence.

    Structurally invalid or inconsistent objects raise ValueError. Unhealthy,
    stale, or generation-skewed resources return no observation instead of
    pretending that a recent reconciliation proves runtime freshness.
    """
    cr = _object(resource, "AIBOM")
    if cr.get("apiVersion") != API_VERSION or cr.get("kind") != "AIBOM":
        raise ValueError("unsupported AIBOM API version or kind")
    metadata = _object(cr.get("metadata"), "metadata")
    spec = _object(cr.get("spec"), "spec")
    status = _object(cr.get("status"), "status")
    namespace = string(metadata.get("namespace"), "metadata.namespace")
    name = string(metadata.get("name"), "metadata.name")
    ref = _object(spec.get("workloadRef"), "spec.workloadRef")
    target = workload(f"{namespace}/{string(ref.get('name'), 'workloadRef.name')}")
    if spec.get("bomFormat") != "CycloneDX" or spec.get("bomSpecVersion") != "1.6":
        raise ValueError("unsupported AIBOM spec BOM format")
    summary = status.get("summary")
    if summary is not None:
        summary = _object(summary, "status.summary")
        _matching_coordinates(_object(summary.get("workload"), "summary.workload"), ref, namespace)

    reasons: list[str] = []
    generation = metadata.get("generation")
    if (type(generation) is not int or generation < 1 or
            type(status.get("observedGeneration")) is not int or
            status["observedGeneration"] != generation):
        reasons.append("AIBOM_GENERATION_NOT_OBSERVED")
    conditions = status.get("conditions", [])
    if not isinstance(conditions, list) or any(not isinstance(c, dict) for c in conditions):
        raise ValueError("invalid AIBOM conditions")
    names = [c.get("type") for c in conditions]
    if any(not isinstance(name, str) or not name for name in names):
        raise ValueError("invalid AIBOM condition type")
    if len(names) != len(set(names)):
        raise ValueError("duplicate AIBOM condition types")
    by_type = {c["type"]: c.get("status") for c in conditions if isinstance(c.get("type"), str)}
    if any(value not in ("True", "False", "Unknown") for value in by_type.values()):
        raise ValueError("invalid AIBOM condition status")
    if by_type.get("Ready") != "True":
        reasons.append("AIBOM_NOT_READY")
    if by_type.get("Stale") == "True":
        reasons.append("AIBOM_SOURCE_STALE")
    if summary is None:
        reasons.append("AIBOM_SUMMARY_MISSING")
    observed_at = status.get("lastReconciled")
    if observed_at is None:
        reasons.append("AIBOM_LAST_RECONCILED_MISSING")
    else:
        timestamp(observed_at)
    if reasons:
        return AdaptedAIBOM(None, tuple(sorted(reasons)))

    # Source health is only necessary, never sufficient: the CR itself is
    # unauthenticated, and a model's "signed=verified" label is not reverified.
    assert summary is not None
    models = summary.get("models", [])
    if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
        raise ValueError("invalid model summaries")
    identities: set[str] = set()
    confidences: set[str] = set()
    for model in models:
        identities.add(string(model.get("identity"), "model.identity"))
        conf = model.get("confidence")
        if conf not in ("declared", "inferred"):
            raise ValueError("unknown model confidence")
        confidences.add(conf)
        if model.get("signed", "unsigned") not in ("unsigned", "claimed", "verified"):
            raise ValueError("unknown model signing state")
    model_ref = next(iter(identities)) if len(identities) == 1 else None
    confidence = "declared" if model_ref and confidences == {"declared"} else (
        "inferred" if model_ref else "unresolved"
    )
    if len(identities) > 1:
        reasons.append("MULTIPLE_MODEL_IDENTITIES")
    if not model_ref:
        reasons.append("MODEL_IDENTITY_UNRESOLVED")
    reasons.extend(_check_inline_document(status))
    reasons.extend(("MODEL_DIGEST_UNAVAILABLE_FROM_SUMMARY", "IMAGE_DIGEST_UNAVAILABLE_FROM_SUMMARY",
                    "AICR_RECIPE_UNAVAILABLE_FROM_AIBOM", "MODEL_SIGNATURE_NOT_INDEPENDENTLY_VERIFIED",
                    "CR_PROVENANCE_NOT_AUTHENTICATED", "RECONCILE_TIME_NOT_EXECUTION_TIME"))
    ob = Observation.parse({"workload": target, "model_ref": model_ref, "model_digest": None,
                            "image_digest": None, "platform_recipe_digest": None,
                            "observed_at": observed_at, "model_confidence": confidence,
                            "evidence_locator": f"aibom://{namespace}/{name}", "source": SOURCE_VERSION})
    return AdaptedAIBOM(ob, tuple(sorted(reasons)))
