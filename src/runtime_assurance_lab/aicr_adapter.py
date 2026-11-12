"""Bounded, read-only adapter for an AICR v1.2.0 resolved RecipeResult JSON.

Sources (Apache-2.0, schema used for interoperability; no source copied):
https://github.com/NVIDIA/aicr/blob/v1.2.0/api/aicr/v1/schemas/RecipeResult.schema.json
https://github.com/NVIDIA/aicr/blob/v1.2.0/pkg/recipe/metadata.go

A hash match proves only *byte equality* to a caller-supplied digest. It does
not authenticate the digest, prove a deployment, or establish model identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .contracts import Intent, digest, string
from .json_strict import loads_strict

SOURCE_VERSION = "NVIDIA/aicr/v1.2.0"
API_VERSION = "aicr.run/v1"
KIND = "RecipeResult"
MAX_RECIPE_BYTES = 8 * 1024 * 1024
MAX_COMPONENTS = 2048


@dataclass(frozen=True, slots=True)
class PinnedRecipe:
    sha256: str
    component_names: tuple[str, ...]
    intent_category: str | None
    limitations: tuple[str, ...]
    source_version: str = SOURCE_VERSION


def pin_recipe(raw: bytes, expected_digest: str, intent: Intent) -> PinnedRecipe:
    """Parse an AICR resolved recipe and bind exact bytes to an external pin.

    `intent` and `expected_digest` are **supplied** by the caller; their
    signatures/provenance are NOT verified by this function. An invalid pin,
    parse, version, or ambiguous component identity must fail closed.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RECIPE_BYTES:
        raise ValueError("AICR recipe must be bounded nonempty bytes")
    digest(expected_digest, required=True)
    if intent.platform_recipe_digest != expected_digest:
        raise ValueError("recipe pin does not match intent platform_recipe_digest")
    actual = f"sha256:{sha256(raw).hexdigest()}"
    if actual != expected_digest:
        raise ValueError("AICR recipe bytes do not match pinned digest")
    try:
        data = loads_strict(raw)
    except (UnicodeDecodeError, RecursionError) as exc:
        raise ValueError("AICR recipe is not valid strict UTF-8 JSON") from exc
    if not isinstance(data, dict) or data.get("apiVersion") != API_VERSION or data.get("kind") != KIND:
        raise ValueError("unsupported AICR resolved RecipeResult kind/version")
    for field in ("componentRefs", "criteria", "deploymentOrder", "metadata"):
        if field not in data:
            raise ValueError(f"AICR RecipeResult missing required field: {field}")
    meta = data["metadata"]
    if not isinstance(meta, dict):
        raise ValueError("AICR recipe metadata must be object")
    criteria = data["criteria"]
    category: str | None = None
    limitations = ["AICR_RECIPE_NOT_ATTESTED", "AICR_RECIPE_NOT_DEPLOYMENT_PROOF"]
    if criteria is None:
        limitations.append("AICR_CRITERIA_UNSPECIFIED")
    elif not isinstance(criteria, dict):
        raise ValueError("AICR recipe criteria must be object or null")
    else:
        if "intent" in criteria:
            category = string(criteria["intent"], "criteria.intent")
            if category not in ("inference", "training", "any"):
                raise ValueError("unsupported AICR recipe intent category")
        else:
            limitations.append("AICR_INTENT_CATEGORY_UNSPECIFIED")
        for field in ("service", "accelerator", "os", "platform"):
            if field in criteria:
                string(criteria[field], f"criteria.{field}")
        if "nodes" in criteria and (type(criteria["nodes"]) is not int or criteria["nodes"] < 0):
            raise ValueError("invalid AICR criteria.nodes")
    components = data["componentRefs"]
    if components is None:
        components = []
    if not isinstance(components, list) or len(components) > MAX_COMPONENTS:
        raise ValueError("invalid/oversized AICR componentRefs")
    names: list[str] = []
    for c in components:
        if not isinstance(c, dict):
            raise ValueError("AICR componentRef must be object")
        for field in ("name", "type"):
            string(c.get(field), f"componentRefs.{field}")
        # Official AICR v1.2.0 RecipeResult testdata permits source="" for
        # local components carrying manifestFiles. The upstream JSON Schema
        # requires `source` to be a *string*, not a nonempty string. Preserve
        # fail-closed semantics for absent source or empty sources without
        # independently identified local manifests.
        source = c.get("source")
        if type(source) is not str:
            raise ValueError("componentRefs.source must be a string")
        if source:
            string(source, "componentRefs.source")
        else:
            manifests = c.get("manifestFiles")
            if (type(manifests) is not list or not manifests or len(manifests) > MAX_COMPONENTS or
                    any(type(path) is not str or not path.strip() or len(path) > 500 for path in manifests)):
                raise ValueError("empty source requires explicit bounded local manifestFiles")
            if "AICR_LOCAL_MANIFEST_SOURCE_UNATTESTED" not in limitations:
                limitations.append("AICR_LOCAL_MANIFEST_SOURCE_UNATTESTED")
        names.append(c["name"])
    if len(names) != len(set(names)):
        raise ValueError("duplicate AICR componentRef names")
    order = data["deploymentOrder"]
    if order is not None:
        if not isinstance(order, list) or len(order) > MAX_COMPONENTS:
            raise ValueError("invalid/oversized AICR deploymentOrder")
        if any(not isinstance(name, str) or not name.strip() or len(name) > 500 for name in order):
            raise ValueError("invalid AICR deploymentOrder member")
        if len(order) != len(set(order)):
            raise ValueError("duplicate AICR deploymentOrder member")
    if not names:
        limitations.append("AICR_COMPONENT_REFS_EMPTY")
    return PinnedRecipe(actual, tuple(names), category, tuple(sorted(limitations)))
