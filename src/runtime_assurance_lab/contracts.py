"""Typed, deliberately narrow boundary for offline AICR/AIBOM-normalized fixtures.

Do not mistake model identity *claims* here for runtime execution attestation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Literal, Mapping, Any

Confidence = Literal["verified", "declared", "inferred", "unresolved"]
Status = Literal["OK", "DRIFT", "UNKNOWN", "STALE"]
HEX_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
WORKLOAD_ID = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?/[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$")


def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid ISO-8601 timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp requires timezone")
    return dt.astimezone(timezone.utc)


def digest(value: str | None, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not HEX_SHA256.fullmatch(value):
        raise ValueError("digest must be sha256:<64 lowercase hex>")
    return value


def string(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise ValueError(f"{key} must be nonempty bounded string")
    return value


def workload(value: Any) -> str:
    v = string(value, "workload")
    if not WORKLOAD_ID.fullmatch(v):
        raise ValueError("workload must be namespace/name")
    return v


@dataclass(frozen=True, slots=True)
class Intent:
    workload: str
    model_ref: str
    model_digest: str
    image_digest: str
    platform_recipe_digest: str

    @classmethod
    def parse(cls, data: Mapping[str, Any]) -> "Intent":
        if not isinstance(data, dict) or set(data) != {"workload", "model_ref", "model_digest", "image_digest", "platform_recipe_digest"}:
            raise ValueError("invalid intent fields")
        return cls(workload(data["workload"]), string(data["model_ref"], "model_ref"),
                   digest(data["model_digest"], required=True), digest(data["image_digest"], required=True),
                   digest(data["platform_recipe_digest"], required=True))


@dataclass(frozen=True, slots=True)
class Observation:
    workload: str
    model_ref: str | None
    model_digest: str | None
    image_digest: str | None
    platform_recipe_digest: str | None
    observed_at: datetime
    model_confidence: Confidence
    evidence_locator: str
    source: str

    @classmethod
    def parse(cls, data: Mapping[str, Any]) -> "Observation":
        expected = {"workload", "model_ref", "model_digest", "image_digest", "platform_recipe_digest", "observed_at", "model_confidence", "evidence_locator", "source"}
        if not isinstance(data, dict) or set(data) != expected:
            raise ValueError("invalid observation fields")
        conf = data["model_confidence"]
        if conf not in ("verified", "declared", "inferred", "unresolved"):
            raise ValueError("invalid confidence")
        ref = data["model_ref"]
        return cls(workload(data["workload"]), string(ref, "model_ref") if ref is not None else None,
                   digest(data["model_digest"], required=False), digest(data["image_digest"], required=False),
                   digest(data["platform_recipe_digest"], required=False), timestamp(data["observed_at"]),
                   conf, string(data["evidence_locator"], "evidence_locator"), string(data["source"], "source"))


@dataclass(frozen=True, slots=True)
class Finding:
    workload: str
    status: Status
    rules: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"workload": self.workload, "status": self.status, "rules": list(self.rules)}
