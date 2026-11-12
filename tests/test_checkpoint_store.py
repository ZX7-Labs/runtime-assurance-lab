"""M7: explicit operator-pinned, local-only SQLite replay checkpoint experiment."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

from runtime_assurance_lab.checkpoint_store import bootstrap, consume
from runtime_assurance_lab.evidence import canonical
from runtime_assurance_lab.source_auth import GENESIS_HEAD
from test_source_auth import NOW, make_source

ROOT = Path(__file__).resolve().parents[1]


def start(path, material=None):
    material = material or make_source()
    pin = bootstrap(path, source_id="approved-fixture-source", workload_id="lab/demo",
                    expected_authority_sha256=material["expected_authority_sha256"],
                    expected_intent_sha256=material["expected_intent_sha256"])
    return material, pin


def use(path, material, pin):
    return consume(path, source_id="approved-fixture-source", workload_id="lab/demo",
                   expected_state_sha256=pin,
                   expected_authority_sha256=material["expected_authority_sha256"],
                   expected_intent_sha256=material["expected_intent_sha256"],
                   intent_bytes=material["intent_bytes"], observation_bytes=material["observation_bytes"],
                   attestation_bytes=material["attestation_bytes"], authority_bytes=material["authority_bytes"],
                   now=NOW)


def test_explicit_bootstrap_and_durable_restart_and_sequence(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    first = use(db, material, pin)
    assert first.committed and first.assessment.source_authenticated
    assert first.assessment.finding.status == "OK"
    assert first.new_state_sha256 != pin
    # Separate second process-like call: no in-memory state required.
    second_material = make_source(sequence=2,
        previous=first.assessment.next_checkpoint["last_head"])
    second = use(db, second_material, first.new_state_sha256)
    assert second.committed and second.assessment.finding.status == "OK"
    assert second.assessment.next_checkpoint["next_sequence"] == 3
    assert second.new_state_sha256 not in (pin, first.new_state_sha256)


def test_replay_old_pin_and_old_signature_never_advance(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    first = use(db, material, pin)
    assert first.committed
    denied = use(db, material, pin)
    assert not denied.committed and denied.assessment.finding.status == "UNKNOWN"
    assert denied.assessment.finding.rules == ("CHECKPOINT_ANCHOR_MISMATCH",)
    replay = use(db, material, first.new_state_sha256)
    assert replay.assessment.finding.rules == ("SOURCE_REPLAY_OR_SEQUENCE_GAP",)
    good_second = make_source(sequence=2, previous=first.assessment.next_checkpoint["last_head"])
    assert use(db, good_second, first.new_state_sha256).committed


def test_bad_signature_cannot_burn_valid_sequence(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    forged = dict(material)
    proof = json.loads(forged["attestation_bytes"])
    proof["signature"] = "AA=="
    forged["attestation_bytes"] = canonical(proof)
    invalid = use(db, forged, pin)
    assert not invalid.committed
    assert invalid.assessment.finding.rules == ("SOURCE_SIGNATURE_INVALID",)
    legitimate = use(db, material, pin)
    assert legitimate.committed and legitimate.assessment.finding.status == "OK"


def test_counterfeit_root_and_intent_cannot_advance(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    forged = dict(material)
    forged["expected_authority_sha256"] = "sha256:" + "a" * 64
    wrong = use(db, forged, pin)
    assert wrong.assessment.finding.rules == ("CHECKPOINT_POLICY_PIN_MISMATCH",)
    assert not wrong.committed
    forged2 = dict(material)
    forged2["expected_intent_sha256"] = "sha256:" + "b" * 64
    wrong2 = use(db, forged2, pin)
    assert wrong2.assessment.finding.rules == ("CHECKPOINT_POLICY_PIN_MISMATCH",)
    assert use(db, material, pin).committed


def test_rollback_db_snapshot_detected_against_independent_new_pin(tmp_path):
    db = tmp_path / "state.sqlite"
    copy = tmp_path / "old.sqlite"
    material, pin = start(db)
    shutil.copyfile(db, copy)
    first = use(db, material, pin)
    assert first.committed
    # Simulated attacker restores old DB while the operator retains NEW pin.
    shutil.copyfile(copy, db)
    new_sig = make_source(sequence=2, previous=first.assessment.next_checkpoint["last_head"])
    refused = use(db, new_sig, first.new_state_sha256)
    assert refused.assessment.finding.rules == ("CHECKPOINT_ANCHOR_MISMATCH",)
    assert not refused.committed
    # If operator also accepts a reverted pin, this local system cannot detect the
    # rollback. The test intentionally does NOT claim such attackers are defeated.


def test_same_sequence_concurrent_calls_only_one_commits(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(use, db, material, pin) for _ in range(2)]
        results = [f.result(timeout=10) for f in futures]
    assert sum(x.committed for x in results) == 1
    assert sorted(x.assessment.finding.status for x in results) == ["OK", "UNKNOWN"]
    assert {x.assessment.finding.rules for x in results if not x.committed} == {
        ("CHECKPOINT_ANCHOR_MISMATCH",)}


def test_verified_drift_consumes_sequence_but_does_not_report_ok(tmp_path):
    db = tmp_path / "state.sqlite"
    material = make_source(observation_change={"model_digest": "sha256:" + "b" * 64})
    material, pin = start(db, material)
    result = use(db, material, pin)
    assert result.committed and result.assessment.source_authenticated
    assert result.assessment.finding.status == "DRIFT"
    assert result.new_state_sha256 and result.new_state_sha256 != pin


def test_bootstrap_does_not_overwrite_existing_and_no_implicit_creation(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    with pytest.raises(FileExistsError):
        start(db)
    assert use(db, material, pin).committed
    with pytest.raises(ValueError, match="explicit operator bootstrap"):
        use(tmp_path / "missing.sqlite", material, pin)


def test_bootstrap_genesis_and_input_validation(tmp_path):
    material = make_source()
    kw = dict(source_id="approved-fixture-source", workload_id="lab/demo",
              expected_authority_sha256=material["expected_authority_sha256"],
              expected_intent_sha256=material["expected_intent_sha256"])
    with pytest.raises(ValueError, match="genesis"):
        bootstrap(tmp_path / "bad.sqlite", **kw, expected_sequence=2, expected_prev_head=GENESIS_HEAD)
    with pytest.raises(ValueError, match="checkpoint sequence"):
        bootstrap(tmp_path / "bad.sqlite", **kw, expected_sequence=True)
    assert not (tmp_path / "bad.sqlite").exists()
    assert bootstrap(tmp_path / "good.sqlite", **kw).startswith("sha256:")


def test_corrupted_sqlite_state_never_returns_ok(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE checkpoints SET last_head=?", ("sha256:" + "b" * 64,))
    # An attacker who modifies the DB without the independent pin will be caught.
    denied = use(db, material, pin)
    assert not denied.committed
    assert denied.assessment.finding.rules == ("CHECKPOINT_STATE_INVALID",)


def test_tampered_database_with_invalid_schema_cannot_yield_ok(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    with sqlite3.connect(db) as conn:
        conn.execute("DROP TABLE checkpoints")
    with pytest.raises(sqlite3.OperationalError):
        use(db, material, pin)


def test_external_pin_is_required(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    with pytest.raises(ValueError, match="digest"):
        use(db, material, "")
    assert use(db, material, pin).committed


def test_cli_bootstrap_consume_and_replay(tmp_path):
    db = tmp_path / "state.sqlite"
    material = make_source()
    for name, payload in (("intent", material["intent_bytes"]),
                           ("observation", material["observation_bytes"]),
                           ("attestation", material["attestation_bytes"]),
                           ("authority", material["authority_bytes"])):
        (tmp_path / (name + ".json")).write_bytes(payload)

    def invoke(*args):
        return subprocess.run([sys.executable, "-m", "runtime_assurance_lab.cli", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=15)

    init = invoke("checkpoint-init-offline", "--state-db", db,
                  "--source-id", "approved-fixture-source", "--workload", "lab/demo",
                  "--expected-authority-sha256", material["expected_authority_sha256"],
                  "--expected-intent-sha256", material["expected_intent_sha256"])
    assert init.returncode == 0, init.stderr
    pin = json.loads(init.stdout)["state_sha256"]
    flags = ("--state-db", db, "--source-id", "approved-fixture-source", "--workload", "lab/demo",
             "--expected-authority-sha256", material["expected_authority_sha256"],
             "--expected-intent-sha256", material["expected_intent_sha256"],
             "--expected-state-sha256", pin, "--now", NOW.isoformat(),
             "--intent", tmp_path / "intent.json", "--observation", tmp_path / "observation.json",
             "--attestation", tmp_path / "attestation.json", "--authority", tmp_path / "authority.json")
    first = invoke("evaluate-authenticated-stateful", *flags)
    assert first.returncode == 0, first.stderr
    out = json.loads(first.stdout)
    assert out["checkpoint_committed"] and out["source_authenticated"] and out["status"] == "OK"
    replay = invoke("evaluate-authenticated-stateful", *flags)
    assert replay.returncode == 2, replay.stderr
    assert json.loads(replay.stdout)["rules"] == ["CHECKPOINT_ANCHOR_MISMATCH"]


def test_failed_sqlite_commit_never_returns_authenticated_ok_or_consumes(monkeypatch, tmp_path):
    from runtime_assurance_lab import checkpoint_store as module

    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    real = module.sqlite3.connect

    class InjectFailedCommit:
        def __init__(self, conn):
            self.conn = conn

        def execute(self, *a, **kw):
            return self.conn.execute(*a, **kw)

        def commit(self):
            raise sqlite3.OperationalError("simulated checkpoint write failure")

        def rollback(self):
            self.conn.rollback()

        def close(self):
            self.conn.close()

    with monkeypatch.context() as scoped:
        scoped.setattr(module.sqlite3, "connect", lambda *a, **kw: InjectFailedCommit(real(*a, **kw)))
        with pytest.raises(sqlite3.OperationalError, match="simulated checkpoint write failure"):
            use(db, material, pin)
    assert use(db, material, pin).committed


def test_local_database_is_not_an_independent_anti_rollback_root(tmp_path):
    # Negative control: restoring BOTH the SQLite file and the operator-supplied
    # state pin (i.e. a compromised external anchor) allows replay. This
    # explicitly documents the limitation; it is NOT a passing security gate.
    db = tmp_path / "state.sqlite"
    old = tmp_path / "old.sqlite"
    material, pin = start(db)
    shutil.copyfile(db, old)
    assert use(db, material, pin).committed
    shutil.copyfile(old, db)
    replay_with_reverted_pin = use(db, material, pin)
    assert replay_with_reverted_pin.committed
    assert replay_with_reverted_pin.assessment.finding.status == "OK"


def test_database_symlink_not_used_as_checkpoint(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    redirect = tmp_path / "redirect.sqlite"
    redirect.symlink_to(db)
    with pytest.raises(ValueError, match="symlink"):
        use(redirect, material, pin)
    with pytest.raises(FileExistsError):
        start(redirect)


def test_new_checkpoint_has_restricted_file_permissions(tmp_path):
    import stat
    db = tmp_path / "state.sqlite"
    start(db)
    assert stat.S_IMODE(db.stat().st_mode) & 0o077 == 0


def test_cli_broken_database_exits_nonzero_without_authenticated_result(tmp_path):
    db = tmp_path / "state.sqlite"
    material, pin = start(db)
    with sqlite3.connect(db) as conn:
        conn.execute("DROP TABLE checkpoints")
    result = subprocess.run(
        [sys.executable, "-m", "runtime_assurance_lab.cli", "evaluate-authenticated-stateful",
         "--state-db", str(db), "--source-id", "approved-fixture-source",
         "--workload", "lab/demo", "--expected-state-sha256", pin,
         "--expected-authority-sha256", material["expected_authority_sha256"],
         "--expected-intent-sha256", material["expected_intent_sha256"],
         "--intent", str(ROOT / "fixtures" / "intent.json"),
         "--observation", str(ROOT / "fixtures" / "clean.json"),
         "--attestation", str(ROOT / "fixtures" / "clean.json"),
         "--authority", str(ROOT / "fixtures" / "clean.json"),
         "--now", NOW.isoformat()], cwd=ROOT, capture_output=True, text=True, timeout=15)
    assert result.returncode == 3
    assert "OperationalError" in result.stderr
    assert '"status": "OK"' not in result.stdout
