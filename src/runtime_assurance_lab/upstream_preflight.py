"""Read-only independent public upstream test-fixture preflight (NOT G4).

No Kubernetes clients, credentials, binary execution, or attestation claims.
Only two immutable source paths from Google k8s-aibom and NVIDIA AICR are
permitted. A Git blob hash checks published byte *identity*, not signer trust.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha1, sha256
import json
from typing import Any, Mapping
from urllib import request

from .aibom_adapter import normalize_aibom
from .aicr_adapter import pin_recipe
from .contracts import Intent
from .json_strict import loads_strict

SCHEMA = "ral-public-upstream-testdata-preflight-v1"
DECISION = "PAUSE_PRODUCT_BUILD"
MAX_SOURCE_BYTES = 256 * 1024


@dataclass(frozen=True, slots=True)
class SourcePin:
    key: str
    repository: str
    commit: str
    path: str
    git_blob_sha1: str
    size_bytes: int

    @property
    def raw_url(self) -> str:
        return f"https://raw.githubusercontent.com/{self.repository}/{self.commit}/{self.path}"


# Independently inspected upstream Git trees at fixed upstream tags; these are
# hardcoded review inputs, NOT caller-configurable URLs/digests or trust roots.
PINS: tuple[SourcePin, ...] = (
    SourcePin("google_bom", "GoogleCloudPlatform/k8s-aibom",
              "47bf6418e40eee22905973528b879dc075181b3f",
              "internal/bom/testdata/golden/vllm-deployment-output.json",
              "b708db2f5a67c2210d29e712a7dd4f8f59487635", 6387),
    SourcePin("nvidia_recipe", "NVIDIA/aicr",
              "935e0746dc54da890a23c1ecca998244b3a25de7",
              "pkg/operator/aicrjob/testdata/v1.1.2/recipe-h100-eks-ubuntu-training.json",
              "7aefe761a870efcc7e74971b8a9d23b093f2918e", 105200),
)
PINS_BY_KEY = {x.key: x for x in PINS}


def git_blob_sha1(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def verify_source_bytes(raw: bytes, pin: SourcePin) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise ValueError("upstream fixture must be bounded nonempty bytes")
    if len(raw) != pin.size_bytes or git_blob_sha1(raw) != pin.git_blob_sha1:
        raise ValueError("upstream fixture bytes differ from pinned Git object")
    try:
        document = loads_strict(raw)
    except (UnicodeDecodeError, RecursionError, OverflowError) as exc:
        raise ValueError("upstream fixture is invalid strict JSON") from exc
    if type(document) is not dict:
        raise ValueError("upstream JSON fixture must be object")
    return {"id": pin.key, "repository": pin.repository, "commit": pin.commit,
            "path": pin.path, "git_blob_sha1": pin.git_blob_sha1,
            "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
            "source_kind": "PUBLIC_UPSTREAM_REPOSITORY_TEST_FIXTURE", "document": document}


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        raise ValueError("upstream public fixture redirect is forbidden")


def download_public_fixtures(*, opener: Any = None) -> dict[str, bytes]:
    """Explicit, narrowly scoped unauthenticated public reads only.

    Called ONLY via --fetch-public-testdata, never by unit tests, importing
    this module, or any product runtime command.
    """
    client = opener if opener is not None else request.build_opener(_NoRedirect)
    assets: dict[str, bytes] = {}
    for pin in PINS:
        with client.open(pin.raw_url, timeout=15) as response:
            if response.geturl() != pin.raw_url:
                raise ValueError("upstream read redirected outside immutable source")
            if response.getcode() != 200:
                raise ValueError("upstream fixture fetch returned non-200 status")
            raw = response.read(MAX_SOURCE_BYTES + 1)
        verify_source_bytes(raw, pin)
        assets[pin.key] = raw
    return assets


def _properties(raw: Any) -> dict[str, str]:
    if type(raw) is not list or len(raw) > 1000:
        raise ValueError("invalid or oversized upstream CycloneDX property list")
    result: dict[str, str] = {}
    for prop in raw:
        if (type(prop) is not dict or type(prop.get("name")) is not str or
            type(prop.get("value")) is not str):
            raise ValueError("invalid upstream CycloneDX property")
        name = prop["name"]
        if name in result and result[name] != prop["value"]:
            raise ValueError("contradictory upstream CycloneDX property")
        result[name] = prop["value"]
    return result


def inspect_google_bom(bom: dict[str, Any]) -> dict[str, Any]:
    """Independent evidence extraction, not another BOM parser/controller."""
    if bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
        raise ValueError("unsupported Google upstream BOM version")
    metadata = bom.get("metadata")
    if type(metadata) is not dict or type(metadata.get("component")) is not dict:
        raise ValueError("missing upstream BOM workload metadata")
    identity = _properties(metadata["component"].get("properties"))
    for name in ("aibom.workload.name", "aibom.workload.namespace", "aibom.workload.kind", "aibom.workload.category"):
        if not identity.get(name):
            raise ValueError("missing upstream BOM workload coordinate")
    components = bom.get("components")
    if type(components) is not list or not 0 < len(components) <= 2048:
        raise ValueError("invalid upstream BOM component list")
    models: list[dict[str, str]] = []
    container_images: list[str] = []
    for component in components:
        if type(component) is not dict or type(component.get("type")) is not str:
            raise ValueError("invalid upstream BOM component")
        props = _properties(component.get("properties", []))
        if component["type"] == "machine-learning-model":
            name = component.get("name")
            if type(name) is not str or not name:
                raise ValueError("empty upstream model name")
            conf = props.get("aibom.confidence")
            if conf not in ("declared", "inferred"):
                raise ValueError("unsupported upstream model confidence")
            models.append({"name": name, "confidence": conf,
                           "evidence_locator": props.get("aibom.evidence.locator", "")})
        if component["type"] == "container":
            hashes = component.get("hashes", [])
            if type(hashes) is not list:
                raise ValueError("invalid upstream container hashes")
            for item in hashes:
                if type(item) is not dict:
                    raise ValueError("invalid upstream container hash entry")
                if item.get("alg") == "SHA-256":
                    value = item.get("content")
                    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                        raise ValueError("malformed upstream container digest")
                    container_images.append("sha256:" + value)
    return {"component_count": len(components), "model_claim_components": len(models),
            "distinct_model_names": sorted({m["name"] for m in models}),
            "image_sha256_claims": sorted(set(container_images)),
            "category": identity["aibom.workload.category"],
            "workload_coordinates": {k: identity["aibom.workload." + k]
                                     for k in ("namespace", "name", "kind")},
            "model_evidence_locator_count": sum(bool(m["evidence_locator"]) for m in models),
            "models": models}


def analyze_public_upstream_fixtures(raw_assets: Mapping[str, bytes],
                                     *, pins: tuple[SourcePin, ...] = PINS) -> dict[str, Any]:
    """Do not correlate unrelated public test fixtures into a runtime assertion."""
    if set(raw_assets) != {"google_bom", "nvidia_recipe"} or {p.key for p in pins} != set(raw_assets):
        raise ValueError("both exact pinned upstream public fixtures are required")
    provenance = {pin.key: verify_source_bytes(raw_assets[pin.key], pin) for pin in pins}
    bom = provenance["google_bom"]["document"]
    recipe = provenance["nvidia_recipe"]["document"]
    existing = inspect_google_bom(bom)
    expected_version = recipe.get("apiVersion")
    if recipe.get("kind") != "RecipeResult" or expected_version != "aicr.run/v1":
        raise ValueError("unsupported NVIDIA upstream RecipeResult kind/version")
    actual_recipe_sha = "sha256:" + sha256(raw_assets["nvidia_recipe"]).hexdigest()
    names = existing["distinct_model_names"]
    if len(names) != 1 or not existing["image_sha256_claims"]:
        raise ValueError("test fixture lacks required controls for this fixed preflight")
    coord = existing["workload_coordinates"]
    intent = Intent.parse({"workload": coord["namespace"] + "/" + coord["name"],
                           "model_ref": names[0], "model_digest": "sha256:" + "0" * 64,
                           "image_digest": existing["image_sha256_claims"][0],
                           "platform_recipe_digest": actual_recipe_sha})
    pinned = pin_recipe(raw_assets["nvidia_recipe"], actual_recipe_sha, intent)
    # This CR is *constructed*, not exported from a Kubernetes controller.
    # Its READY/GENERATION state is explicitly invented for adapter-coverage
    # testing, so it must never be presented as actual runtime evidence.
    observed_at = bom["metadata"].get("timestamp")
    if type(observed_at) is not str:
        raise ValueError("upstream BOM lacks a timestamp")
    group = _properties(bom["metadata"]["component"]["properties"]).get("aibom.workload.group", "")
    apiversion = (group + "/" if group else "") + "v1"
    resource = {"apiVersion": "aibom.k8saibom.dev/v1beta1", "kind": "AIBOM",
                "metadata": {"name": "preflight-synthetic-wrapper", "namespace": coord["namespace"], "generation": 1},
                "spec": {"workloadRef": {"apiVersion": apiversion, "kind": coord["kind"], "name": coord["name"]},
                         "bomFormat": "CycloneDX", "bomSpecVersion": "1.6"},
                "status": {"observedGeneration": 1, "lastReconciled": observed_at,
                           "conditions": [{"type": "Ready", "status": "True"}, {"type": "Stale", "status": "False"}],
                           "summary": {"workload": {"apiVersion": apiversion, "kind": coord["kind"],
                                                    "namespace": coord["namespace"], "name": coord["name"]},
                                       "models": [{"identity": m["name"], "confidence": m["confidence"],
                                                   "signed": "unsigned"} for m in existing["models"]]},
                           "bomHash": sha256(raw_assets["google_bom"]).hexdigest(),
                           "bomDocument": {"format": "CycloneDX", "specVersion": "1.6",
                                           "sha256": sha256(raw_assets["google_bom"]).hexdigest(),
                                           "size": len(raw_assets["google_bom"]),
                                           "inline": {"data": base64.b64encode(raw_assets["google_bom"]).decode("ascii")}}}}
    adapted = normalize_aibom(resource)
    if adapted.observation is None or adapted.observation.image_digest is not None:
        raise ValueError("unexpected raw BOM to AIBOM adapter promotion")
    if pinned.intent_category == existing["category"]:
        # The fixed samples are intentionally different source workloads.
        raise ValueError("upstream public samples unexpectedly have matching intents; re-review inputs")
    return {"schema": SCHEMA, "decision": DECISION,
            "source_class": "PUBLIC_UPSTREAM_TEST_FIXTURES_NOT_LIVE_OR_SIGNED",
            "upstream_binaries_executed": False,
            "authentic_runtime_assurance": False,
            "independent_git_blob_checks": len(pins),
            "sources": [{key: val[key] for key in ("id", "repository", "commit", "path", "git_blob_sha1", "sha256", "bytes", "source_kind")}
                        for val in (provenance[pin.key] for pin in pins)],
            "baseline_existing_google": {k: v for k, v in existing.items() if k != "models"},
            "nvidia_recipe": {"component_count": len(pinned.component_names), "category": pinned.intent_category,
                              "recipe_pin_integrity_only": True},
            "aibom_adapter_probe": {"wrapper": "SYNTHETIC_NOT_UPSTREAM_CR_EXPORT",
                                    "image_digest_in_original_bom": bool(existing["image_sha256_claims"]),
                                    "image_digest_in_normalized_observation": adapted.observation.image_digest is not None,
                                    "limitations": list(adapted.limitations)},
            "cross_plane_link_verified": False,
            "cross_plane_link_reason": "PUBLIC_SAMPLES_FROM_DIFFERENT_WORKLOAD_TYPES_AND_NO_COMMON_AUTHENTICATED_DEPLOYMENT_ID",
            "independently_demonstrated_incremental_signal": False,
            "limitations": [
                "The upstream public test data are synthetic examples, not authentic live cluster exports.",
                "Git object SHA-1 identity and HTTPS are not Sigstore publisher identity or execution proof.",
                "The AIBOM wrapper is locally constructed and contains invented healthy controller status.",
                "The AICR example documents a training configuration, the Google BOM an inference workload; they must not be joined.",
                "This code inspects raw public fixture semantics but does not execute upstream binaries, clusters, or attestation verifiers.",
            ]}
