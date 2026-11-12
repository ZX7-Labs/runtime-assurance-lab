"""Bounded, offline source-authentication gate with independently pinned inputs.

NOT an upstream Sigstore verifier, attested execution proof, secure storage system,
or trusted-clock implementation. This module accepts caller-supplied *independent*
trust-root/intent pins and a durable last-accepted sequence/head checkpoint.
No trust roots or replay anchors are inferred from the source evidence itself.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .contracts import Finding, Intent, Observation, digest, string, timestamp, workload
from .evidence import canonical
from .evaluate import _evaluate_authenticated_claims
from .json_strict import loads_strict

TRUST_SCHEMA = "ral-trust-authority/v1"
PROOF_SCHEMA = "ral-observation-attestation/v1"
DOMAIN = "runtime-assurance-lab/source-attestation/v1"
GENESIS_HEAD = "sha256:" + "0" * 64
MAX_TRUST_BYTES = 16 * 1024
MAX_PROOF_BYTES = 16 * 1024
MAX_OBSERVATION_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class SourceAssessment:
    finding: Finding
    # Only issued after successful signature/key/scope/sequence/anchor checks.
    next_checkpoint: dict[str, Any] | None
    source_authenticated: bool

    def to_dict(self) -> dict[str, Any]:
        return {**self.finding.to_dict(), "source_authenticated": self.source_authenticated,
                "next_checkpoint": self.next_checkpoint,
                "scope": "authenticated pinned source *assertion*, NOT proof of running model/GPU"}


def _read_document(raw: bytes, label: str, maximum: int) -> dict[str, Any]:
    if type(raw) is not bytes or not (0 < len(raw) <= maximum):
        raise ValueError(f"{label}: invalid bounded bytes")
    try:
        value = loads_strict(raw)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError(f"{label}: malformed UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected object")
    return value


def _sha(data: bytes) -> str:
    return "sha256:" + sha256(data).hexdigest()


def _unknown(intent: Intent, code: str) -> SourceAssessment:
    return SourceAssessment(Finding(intent.workload, "UNKNOWN", (code,)), None, False)


def authenticate_and_evaluate(*, intent_bytes: bytes, observation_bytes: bytes,
                               attestation_bytes: bytes, authority_bytes: bytes,
                               expected_intent_sha256: str,
                               expected_authority_sha256: str,
                               expected_sequence: int, expected_prev_head: str,
                               now: datetime) -> SourceAssessment:
    """Authenticate an observation via a DETACHED signature and independent pins.

    Caller must derive intent/authority hashes from independently controlled
    configuration and expected_sequence/prev_head from durable, anti-rollback
    checkpoint storage. A second attacker-chosen configuration proves nothing.
    Checkpoint advancement is caller-owned and must be atomic and durable.
    """
    # Fail on malformed independent operator parameters rather than silently
    # treating them as source-reported values.
    digest(expected_intent_sha256, required=True)
    digest(expected_authority_sha256, required=True)
    digest(expected_prev_head, required=True)
    if type(expected_sequence) is not int or not (1 <= expected_sequence < 2**63 - 1):
        raise ValueError("expected_sequence must be an externally anchored positive integer")
    if (expected_sequence == 1) != (expected_prev_head == GENESIS_HEAD):
        raise ValueError("genesis head is valid only for sequence 1; non-genesis requires a prior trusted checkpoint")
    if not isinstance(now, datetime):
        raise ValueError("now must be a trusted datetime")
    timestamp(now.isoformat())  # reject naive clock before reviewing attacker evidence
    if type(intent_bytes) is not bytes or not 0 < len(intent_bytes) <= MAX_OBSERVATION_BYTES:
        raise ValueError("invalid intent bytes")
    if _sha(intent_bytes) != expected_intent_sha256:
        # No trusted intent exists if its externally pinned hash differs.
        raise ValueError("independent intent pin mismatch")
    intent = Intent.parse(_read_document(intent_bytes, "intent", MAX_OBSERVATION_BYTES))

    if type(authority_bytes) is not bytes or not 0 < len(authority_bytes) <= MAX_TRUST_BYTES:
        return _unknown(intent, "TRUST_ROOT_INVALID")
    if _sha(authority_bytes) != expected_authority_sha256:
        return _unknown(intent, "TRUST_ROOT_NOT_ANCHORED")
    try:
        authority = _read_document(authority_bytes, "authority", MAX_TRUST_BYTES)
        if set(authority) != {"schema", "source_id", "key_id", "public_key_ed25519", "workloads"} or authority["schema"] != TRUST_SCHEMA:
            return _unknown(intent, "TRUST_ROOT_INVALID")
        source_id = string(authority["source_id"], "source_id")
        key_id = string(authority["key_id"], "key_id")
        scopes = authority["workloads"]
        if not isinstance(scopes, list) or not 1 <= len(scopes) <= 256 or not all(isinstance(x, str) for x in scopes):
            return _unknown(intent, "TRUST_SCOPE_INVALID")
        if len(set(scopes)) != len(scopes) or any(workload(x) != x for x in scopes) or intent.workload not in scopes:
            return _unknown(intent, "TRUST_SCOPE_INVALID")
        key_encoded = authority["public_key_ed25519"]
        if not isinstance(key_encoded, str):
            return _unknown(intent, "TRUST_KEY_INVALID")
        pub_bytes = base64.b64decode(key_encoded, validate=True)
        if len(pub_bytes) != 32 or base64.b64encode(pub_bytes).decode() != key_encoded:
            return _unknown(intent, "TRUST_KEY_INVALID")
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
    except (TypeError, ValueError, UnicodeError, RecursionError, KeyError):
        return _unknown(intent, "TRUST_ROOT_INVALID")

    try:
        observation = Observation.parse(_read_document(observation_bytes, "observation", MAX_OBSERVATION_BYTES))
        evidence = _read_document(attestation_bytes, "attestation", MAX_PROOF_BYTES)
    except (TypeError, ValueError, UnicodeError, RecursionError, KeyError):
        return _unknown(intent, "SOURCE_EVIDENCE_INVALID")
    keys = {"schema", "domain", "source_id", "key_id", "sequence", "prev_head",
            "observation_sha256", "workload", "observed_at", "signature"}
    if set(evidence) != keys or evidence.get("schema") != PROOF_SCHEMA or evidence.get("domain") != DOMAIN:
        return _unknown(intent, "SOURCE_PROOF_INVALID")
    if (evidence["source_id"] != source_id or evidence["key_id"] != key_id
            or observation.source != source_id or evidence["workload"] != intent.workload
            or observation.workload != intent.workload):
        return _unknown(intent, "SOURCE_IDENTITY_MISBOUND")
    if type(evidence["sequence"]) is not int or evidence["sequence"] != expected_sequence:
        return _unknown(intent, "SOURCE_REPLAY_OR_SEQUENCE_GAP")
    if evidence["prev_head"] != expected_prev_head:
        return _unknown(intent, "SOURCE_ROLLBACK_OR_FORK")
    if evidence["observation_sha256"] != _sha(observation_bytes):
        return _unknown(intent, "SOURCE_PAYLOAD_TAMPERED")
    try:
        if timestamp(evidence["observed_at"]) != observation.observed_at:
            return _unknown(intent, "SOURCE_TIMESTAMP_MISBOUND")
        signature = evidence["signature"]
        if not isinstance(signature, str):
            return _unknown(intent, "SOURCE_SIGNATURE_INVALID")
        signature_bytes = base64.b64decode(signature, validate=True)
        if len(signature_bytes) != 64 or base64.b64encode(signature_bytes).decode() != signature:
            return _unknown(intent, "SOURCE_SIGNATURE_INVALID")
        signable = {key: value for key, value in evidence.items() if key != "signature"}
        public_key.verify(signature_bytes, canonical(signable))
    except (InvalidSignature, ValueError, TypeError, UnicodeError, RecursionError):
        return _unknown(intent, "SOURCE_SIGNATURE_INVALID")
    # Evidence digest is computed over the *entire* validated envelope; the
    # caller must persist it outside the source's control BEFORE trusting next.
    checkpoint = {"source_id": source_id, "next_sequence": expected_sequence + 1,
                  "last_head": _sha(canonical(evidence))}
    return SourceAssessment(_evaluate_authenticated_claims(intent, observation, now=now), checkpoint, True)
