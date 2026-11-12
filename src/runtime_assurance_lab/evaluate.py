"""Offline correlation rules. Integrity verification is a separate precondition."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from .contracts import Finding, Intent, Observation

POLICY_VERSION = "ral-intent-observation-v1"


def evaluate(intent: Intent, observation: Observation | None, *, now: datetime,
             max_age_seconds: int = 300, allowed_clock_skew_seconds: int = 30) -> Finding:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now requires timezone")
    if not (1 <= max_age_seconds <= 86400) or not (0 <= allowed_clock_skew_seconds <= 300):
        raise ValueError("invalid freshness policy")
    now = now.astimezone(timezone.utc)
    if observation is None:
        return Finding(intent.workload, "UNKNOWN", ("OBSERVATION_MISSING",))
    if intent.workload != observation.workload:
        return Finding(intent.workload, "UNKNOWN", ("WORKLOAD_MISBOUND",))
    if observation.observed_at > now + timedelta(seconds=allowed_clock_skew_seconds):
        return Finding(intent.workload, "UNKNOWN", ("FUTURE_OBSERVATION",))
    if now - observation.observed_at > timedelta(seconds=max_age_seconds):
        return Finding(intent.workload, "STALE", ("EVIDENCE_EXPIRED",))

    drift: list[str] = []
    unknown: list[str] = []
    for key in ("model_ref", "model_digest", "image_digest", "platform_recipe_digest"):
        actual = getattr(observation, key)
        if actual is None:
            unknown.append(f"{key.upper()}_UNRESOLVED")
        elif actual != getattr(intent, key):
            drift.append(f"{key.upper()}_MISMATCH")
    # Even identical declared or inferred model claims are not proof of model identity.
    if observation.model_confidence != "verified":
        unknown.append("MODEL_NOT_CRYPTO_VERIFIED")
    if drift:
        return Finding(intent.workload, "DRIFT", tuple(sorted(drift + unknown)))
    if unknown:
        return Finding(intent.workload, "UNKNOWN", tuple(sorted(unknown)))
    return Finding(intent.workload, "OK", ())


def naive_baseline(intent: Intent, observation: Observation | None, **_: object) -> Finding:
    """Deliberately limited local comparator, NOT an implementation of upstream AICR/k8s-aibom."""
    if observation is None:
        return Finding(intent.workload, "OK", ())  # blind spot, intentionally measured
    if intent.model_ref != observation.model_ref or intent.image_digest != observation.image_digest:
        return Finding(intent.workload, "DRIFT", ("NAIVE_STRING_MISMATCH",))
    return Finding(intent.workload, "OK", ())
