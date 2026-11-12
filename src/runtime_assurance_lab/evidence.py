"""Signed local claim DAG on an append-only hash chain, NOT a Sigstore replacement.

Trust roots and expected head MUST originate outside the untrusted journal; this
module does not establish actual Kubernetes runtime truth or trusted timestamps.
"""
from __future__ import annotations
import base64
import hashlib
import json
from typing import Any, Mapping
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

DOMAIN = "runtime-assurance-lab-evidence/v1"
GENESIS = "0" * 64
KINDS = {"intent", "observation", "decision"}


def canonical(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate_signer() -> tuple[Ed25519PrivateKey, str]:
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return key, base64.b64encode(pub).decode("ascii")


def append(events: list[dict[str, Any]], kind: str, payload: dict[str, Any],
           refs: list[str], signer_id: str, key: Ed25519PrivateKey) -> dict[str, Any]:
    if kind not in KINDS or not isinstance(payload, dict):
        raise ValueError("invalid event")
    if len(refs) != len(set(refs)):
        raise ValueError("duplicate references")
    previous = sha(canonical(events[-1])) if events else GENESIS
    signable = {"domain": DOMAIN, "seq": len(events), "kind": kind,
                "prev": previous, "refs": refs, "payload_sha256": sha(canonical(payload)),
                "signer_id": signer_id}
    signature = base64.b64encode(key.sign(canonical(signable))).decode("ascii")
    event = {**signable, "payload": payload, "signature": signature}
    events.append(event)
    return event


def head(events: list[dict[str, Any]]) -> str:
    return sha(canonical(events[-1])) if events else GENESIS


def verify(events: list[dict[str, Any]], trust: Mapping[str, tuple[str, str]], *,
           expected_head: str, expected_count: int) -> tuple[bool, str]:
    """trust maps signer_id -> (base64-pubkey, authorized-event-kind).

    Fail closed on unknown roles, mislinked decisions, altered order, truncation.
    expected_head/count are independently anchored, never read from events.
    """
    if (not isinstance(events, list) or not isinstance(trust, Mapping)
            or type(expected_count) is not int or not (0 <= expected_count <= 10000)
            or not isinstance(expected_head, str) or len(expected_head) != 64
            or any(c not in "0123456789abcdef" for c in expected_head)):
        return False, "INVALID_INPUT"
    if len(events) != expected_count:
        return False, "COUNT_MISMATCH"
    seen: dict[str, dict[str, Any]] = {}
    previous = GENESIS
    for index, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != {"domain", "seq", "kind", "prev", "refs", "payload_sha256", "signer_id", "payload", "signature"}:
            return False, "INVALID_ENVELOPE"
        if event["domain"] != DOMAIN or type(event["seq"]) is not int or event["seq"] != index or event["prev"] != previous:
            return False, "BROKEN_CHAIN"
        if not isinstance(event["payload"], dict) or event["kind"] not in KINDS or not isinstance(event["refs"], list):
            return False, "INVALID_CLAIM"
        if not all(isinstance(r, str) for r in event["refs"]) or len(event["refs"]) != len(set(event["refs"])) or any(r not in seen for r in event["refs"]):
            return False, "INVALID_REFERENCES"
        if event["kind"] in {"intent", "observation"} and event["refs"]:
            return False, "UNEXPECTED_PARENTS"
        if event["kind"] == "decision":
            parents = [seen[r] for r in event["refs"]]
            kinds = [p["kind"] for p in parents]
            if len(parents) not in (1, 2) or kinds != (["intent"] if len(parents) == 1 else ["intent", "observation"]):
                return False, "INVALID_DECISION_PARENTS"
            if not all(p["payload"].get("workload") == event["payload"].get("workload") for p in parents):
                return False, "DECISION_WORKLOAD_MISBOUND"
        if event["payload_sha256"] != sha(canonical(event["payload"])):
            return False, "PAYLOAD_TAMPERED"
        if not isinstance(event["signer_id"], str) or not isinstance(event["signature"], str):
            return False, "INVALID_IDENTITY_ENCODING"
        identity = trust.get(event["signer_id"])
        if not isinstance(identity, (tuple, list)) or len(identity) != 2 or identity[1] != event["kind"]:
            return False, "UNAUTHORIZED_SIGNER_OR_KIND"
        try:
            pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(identity[0], validate=True))
            sig = base64.b64decode(event["signature"], validate=True)
            signed = {k: event[k] for k in ("domain", "seq", "kind", "prev", "refs", "payload_sha256", "signer_id")}
            pub.verify(sig, canonical(signed))
        except (ValueError, InvalidSignature, TypeError):
            return False, "INVALID_SIGNATURE"
        previous = sha(canonical(event))
        seen[previous] = event
    if previous != expected_head:
        return False, "HEAD_MISMATCH"
    return True, "VERIFIED_LOCAL_CHAIN"


def verify_decision_semantics(events: list[dict[str, Any]], *, trusted_now: str) -> tuple[bool, str]:
    """Independent deterministic recomputation, after verify() authenticates events.

    The caller must supply a trusted time value independently of journal payloads.
    A locally signed decision is not itself evidence that the evaluator ran.
    """
    from .contracts import Intent, Observation, timestamp
    from .evaluate import POLICY_VERSION, evaluate

    try:
        now = timestamp(trusted_now)
        events_by_hash = {sha(canonical(e)): e for e in events}
        consumed: set[str] = set()
        decisions = 0
        for event in events:
            if event["kind"] != "decision":
                continue
            decisions += 1
            payload = event["payload"]
            if payload.get("evaluated_at") != trusted_now or payload.get("policy_version") != POLICY_VERSION:
                return False, "UNTRUSTED_POLICY_OR_CLOCK"
            refs = event["refs"]
            if len(refs) not in (1, 2) or any(r in consumed for r in refs):
                return False, "REPLAYED_OR_INVALID_CAUSAL_REFERENCE"
            parents = [events_by_hash[r] for r in refs]
            intent = Intent.parse(parents[0]["payload"])
            observation = Observation.parse(parents[1]["payload"]) if len(parents) == 2 else None
            expected = evaluate(intent, observation, now=now).to_dict()
            for key in ("workload", "status", "rules"):
                if payload.get(key) != expected[key]:
                    return False, "DECISION_CONTRADICTS_EVIDENCE"
            consumed.update(refs)
        # Every signed source event must have exactly one certified interpretation.
        source_events = {sha(canonical(e)) for e in events if e["kind"] in ("intent", "observation")}
        if not decisions or consumed != source_events:
            return False, "ORPHANED_EVIDENCE"
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        return False, "INVALID_SEMANTIC_PAYLOAD"
    return True, "DECISIONS_RECOMPUTED"
