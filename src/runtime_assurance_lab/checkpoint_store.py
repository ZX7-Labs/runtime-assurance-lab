"""Offline, single-host transactional replay-checkpoint experiment (NOT a trust root).

The operator MUST hold the expected SHA-256 of the *entire checkpoint state*
independently of this SQLite file. Reading a state hash from the same potentially
rolled-back database and presenting it as trusted defeats rollback protection.
SQLite transactions prevent ordinary concurrent double-consumption, not a
privileged adversary restoring both the database and its external anchor.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from contextlib import closing
from hashlib import sha256
import os
from pathlib import Path
import sqlite3
from typing import Any
from urllib.parse import quote

from .contracts import Finding, digest, string, workload
from .evidence import canonical
from .source_auth import GENESIS_HEAD, SourceAssessment, authenticate_and_evaluate

STATE_SCHEMA = "ral-offline-checkpoint-state/v1"

_CREATE = """CREATE TABLE checkpoints (
    source_id TEXT NOT NULL,
    workload TEXT NOT NULL,
    authority_sha256 TEXT NOT NULL,
    intent_sha256 TEXT NOT NULL,
    next_sequence INTEGER NOT NULL CHECK (next_sequence >= 1),
    last_head TEXT NOT NULL,
    PRIMARY KEY (source_id, workload)
)"""


@dataclass(frozen=True, slots=True)
class Consumed:
    assessment: SourceAssessment
    committed: bool
    new_state_sha256: str | None

    def to_dict(self) -> dict[str, Any]:
        return {**self.assessment.to_dict(), "checkpoint_committed": self.committed,
                "new_state_sha256": self.new_state_sha256,
                "checkpoint_scope": "local transactional simulation; independently held pin required; not a secure anchor"}


def _state(*, source_id: str, workload_id: str, authority_sha256: str,
           intent_sha256: str, next_sequence: int, last_head: str) -> dict[str, Any]:
    string(source_id, "source_id")
    workload(workload_id)
    digest(authority_sha256, required=True)
    digest(intent_sha256, required=True)
    digest(last_head, required=True)
    if type(next_sequence) is not int or not 1 <= next_sequence < 2**63-1:
        raise ValueError("checkpoint sequence out of bounds")
    if (next_sequence == 1) != (last_head == GENESIS_HEAD):
        raise ValueError("genesis checkpoint inconsistent with sequence")
    return {"schema": STATE_SCHEMA, "source_id": source_id, "workload": workload_id,
            "authority_sha256": authority_sha256, "intent_sha256": intent_sha256,
            "next_sequence": next_sequence, "last_head": last_head}


def _hash_state(state: dict[str, Any]) -> str:
    return "sha256:" + sha256(canonical(state)).hexdigest()


def _connect(path: Path, *, create: bool = False) -> sqlite3.Connection:
    # SQLite's URI mode=rw refuses to create missing state on verification.
    # Symlinks to a different DB are refused; path protections are NOT a trust root.
    if path.is_symlink():
        raise ValueError("checkpoint database path cannot be a symlink")
    if not create and not path.is_file():
        raise ValueError("checkpoint database missing; explicit operator bootstrap required")
    uri = "file:" + quote(str(path.absolute()), safe="/") + ("?mode=rwc" if create else "?mode=rw")
    conn = sqlite3.connect(uri, uri=True, timeout=5, isolation_level=None)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
    except BaseException:
        conn.close()
        raise
    return conn


def bootstrap(path: Path, *, source_id: str, workload_id: str,
              expected_authority_sha256: str, expected_intent_sha256: str,
              expected_sequence: int = 1, expected_prev_head: str = GENESIS_HEAD) -> str:
    """Explicit, exclusive operator bootstrap. Never infer pins from source data.

    The caller must independently authenticate every parameter and protect the
    returned state hash *outside* the database. Creating a new database is NOT
    permission to reset a stream that may have processed previous evidence.
    """
    state = _state(source_id=source_id, workload_id=workload_id,
                   authority_sha256=expected_authority_sha256,
                   intent_sha256=expected_intent_sha256,
                   next_sequence=expected_sequence, last_head=expected_prev_head)
    if not isinstance(path, Path) or not path.parent.is_dir():
        raise ValueError("database parent directory must exist")
    # Exclusive new-file creation: refuses overwriting an existing checkpoint.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    conn = _connect(path, create=True)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(_CREATE)
        conn.execute("INSERT INTO checkpoints VALUES (?,?,?,?,?,?)", (
            source_id, workload_id, expected_authority_sha256, expected_intent_sha256,
            expected_sequence, expected_prev_head))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    return _hash_state(state)


def _deny(workload_id: str, reason: str) -> Consumed:
    return Consumed(SourceAssessment(Finding(workload_id, "UNKNOWN", (reason,)), None, False), False, None)


def consume(path: Path, *, source_id: str, workload_id: str,
            expected_state_sha256: str, expected_authority_sha256: str,
            expected_intent_sha256: str, intent_bytes: bytes,
            observation_bytes: bytes, attestation_bytes: bytes,
            authority_bytes: bytes, now: datetime) -> Consumed:
    """Serialize verification and advance only after a successful source signature.

    The caller provides THREE externally pinned values on every invocation:
    root hash, intent hash, and last checkpoint-state hash. All inputs remain
    untrusted, including the SQLite database; do not derive these pins from it.
    """
    string(source_id, "source_id")
    workload(workload_id)
    digest(expected_state_sha256, required=True)
    digest(expected_authority_sha256, required=True)
    digest(expected_intent_sha256, required=True)

    with closing(_connect(path)) as conn:
        conn.execute("BEGIN IMMEDIATE")  # holds SQLite writer lock through verify and durable commit
        try:
            rows = conn.execute(
                "SELECT authority_sha256, intent_sha256, next_sequence, last_head "
                "FROM checkpoints WHERE source_id=? AND workload=?",
                (source_id, workload_id)).fetchall()
            if len(rows) != 1:
                conn.rollback()
                return _deny(workload_id, "CHECKPOINT_STATE_MISSING")
            authority_pin, intent_pin, seq, previous = rows[0]
            try:
                state = _state(source_id=source_id, workload_id=workload_id,
                               authority_sha256=authority_pin, intent_sha256=intent_pin,
                               next_sequence=seq, last_head=previous)
            except (TypeError, ValueError):
                conn.rollback()
                return _deny(workload_id, "CHECKPOINT_STATE_INVALID")
            if _hash_state(state) != expected_state_sha256:
                conn.rollback()
                return _deny(workload_id, "CHECKPOINT_ANCHOR_MISMATCH")
            if authority_pin != expected_authority_sha256 or intent_pin != expected_intent_sha256:
                conn.rollback()
                return _deny(workload_id, "CHECKPOINT_POLICY_PIN_MISMATCH")

            assessment = authenticate_and_evaluate(
                intent_bytes=intent_bytes, observation_bytes=observation_bytes,
                attestation_bytes=attestation_bytes, authority_bytes=authority_bytes,
                expected_intent_sha256=intent_pin, expected_authority_sha256=authority_pin,
                expected_sequence=seq, expected_prev_head=previous, now=now)
            if not assessment.source_authenticated or assessment.next_checkpoint is None:
                conn.rollback()
                return Consumed(assessment, False, None)
            new = assessment.next_checkpoint
            updated = _state(source_id=source_id, workload_id=workload_id,
                             authority_sha256=authority_pin, intent_sha256=intent_pin,
                             next_sequence=new["next_sequence"], last_head=new["last_head"])
            n = conn.execute(
                "UPDATE checkpoints SET next_sequence=?, last_head=? "
                "WHERE source_id=? AND workload=? AND next_sequence=? AND last_head=?",
                (updated["next_sequence"], updated["last_head"], source_id, workload_id, seq, previous))
            if n.rowcount != 1:
                raise RuntimeError("concurrent checkpoint mutation")
            # No assurance result must be returned before this commit succeeds.
            conn.commit()
            return Consumed(assessment, True, _hash_state(updated))
        except BaseException:
            conn.rollback()
            raise
