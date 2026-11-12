"""Cross-plane receipt replay contract; all samples are synthetic."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from runtime_assurance_lab.crossplane_receipt import make_receipt, replay_receipt, LIMITATIONS
from test_integration_performance import invoke

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
INTENT = (FIX / "intent-aicr-synthetic.json").read_bytes()
RECIPE = (FIX / "aicr-recipe-result-synthetic.json").read_bytes()
AIBOM = (FIX / "aibom-v1beta1-synthetic.json").read_bytes()
PIN = json.loads(INTENT)["platform_recipe_digest"]
NOW = "2026-11-12T03:25:00Z"
INPUTS = dict(intent_bytes=INTENT, recipe_bytes=RECIPE, aibom_bytes=AIBOM,
              expected_recipe_sha256=PIN, trusted_now=NOW)


def test_receipt_is_deterministic_and_fails_open_on_no_fields_never():
    a = make_receipt(**INPUTS)
    b = make_receipt(**INPUTS)
    assert a == b
    assert a["decision"]["status"] == "UNKNOWN"
    assert "MODEL_DIGEST_UNRESOLVED" in a["decision"]["rules"]
    assert a["limitations"] == list(LIMITATIONS)
    for source, raw in (("intent", INTENT), ("aicr_recipe", RECIPE), ("aibom", AIBOM)):
        assert a["input_sha256"][source] == "sha256:" + sha256(raw).hexdigest()
    assert a["adapters"]["aicr"]["component_count"] == 1
    assert replay_receipt(a, **INPUTS) == (True, "RAW_SOURCES_AND_DECISION_RECOMPUTED")


@pytest.mark.parametrize("field,alter", [
    ("status", "OK"), ("status", "DRIFT"), ("rules", []),
    ("workload", "different/workload"),
])
def test_forged_replay_result_cannot_pass_even_with_valid_input_hashes(field, alter):
    receipt = make_receipt(**INPUTS)
    receipt["decision"][field] = alter
    assert replay_receipt(receipt, **INPUTS) == (False, "RECEIPT_CONTRADICTS_RAW_SOURCES")


@pytest.mark.parametrize("mutation", [
    lambda x: x.pop("limitations"),
    lambda x: x.update(unchecked_security_claim="trusted"),
    lambda x: x["limitations"].clear(),
    lambda x: x["input_sha256"].update(aibom="sha256:" + "0" * 64),
    lambda x: x["adapters"]["aibom"].update(limitations=[]),
    lambda x: x.update(evaluated_at="2026-11-12T04:25:00+00:00"),
    lambda x: x.update(policy_version="attacker-policy"),
    lambda x: x["adapters"]["aicr"].update(source_version="unreviewed-version"),
    lambda x: x.update(external_recipe_pin="sha256:" + "0" * 64),
])
def test_removed_or_forged_provenance_and_policy_fields_fail_replay(mutation):
    receipt = deepcopy(make_receipt(**INPUTS))
    mutation(receipt)
    assert replay_receipt(receipt, **INPUTS)[0] is False


def test_json_type_confusion_is_rejected_even_when_python_equality_says_equal():
    receipt = make_receipt(**INPUTS)
    receipt["adapters"]["aicr"]["component_count"] = True
    assert True == 1  # Python's equality is not a JSON-type-safe comparator.
    assert replay_receipt(receipt, **INPUTS)[0] is False


def test_changed_raw_input_even_equivalent_json_cannot_replay():
    receipt = make_receipt(**INPUTS)
    for name in ("intent_bytes", "recipe_bytes", "aibom_bytes"):
        changed = {**INPUTS, name: INPUTS[name] + b"\n"}
        verified, reason = replay_receipt(receipt, **changed)
        assert verified is False
        assert reason == ("SOURCE_OR_PIN_INVALID" if name == "recipe_bytes"
                          else "RECEIPT_CONTRADICTS_RAW_SOURCES")


def test_clock_is_independent_of_receipt_and_requires_utc_offset():
    receipt = make_receipt(**INPUTS)
    assert replay_receipt(receipt, **{**INPUTS, "trusted_now": "2026-11-12T03:35:00Z"})[0] is False
    with pytest.raises(ValueError, match="timezone"):
        make_receipt(**{**INPUTS, "trusted_now": "2026-11-12T03:25:00"})


def test_unhealthy_aibom_does_not_become_ok():
    data = json.loads(AIBOM)
    data["status"]["conditions"][0]["status"] = "False"
    raw = json.dumps(data, sort_keys=True).encode()
    changed = make_receipt(**{**INPUTS, "aibom_bytes": raw})
    assert changed["decision"]["status"] == "UNKNOWN"
    assert "OBSERVATION_MISSING" in changed["decision"]["rules"]
    assert "AIBOM_NOT_READY" in changed["adapters"]["aibom"]["limitations"]


def test_invalid_source_rejected_not_reported_as_clean():
    with pytest.raises(ValueError):
        make_receipt(**{**INPUTS, "intent_bytes": b'{"workload":"lab/demo","workload":"lab/demo"}'})
    with pytest.raises(ValueError):
        make_receipt(**{**INPUTS, "aibom_bytes": b'{"bad":NaN}'})
    with pytest.raises(ValueError, match="bounded"):
        make_receipt(**{**INPUTS, "aibom_bytes": b"x" * (8 * 1024 * 1024 + 1)})
    with pytest.raises(ValueError, match="pinned digest"):
        make_receipt(**{**INPUTS, "recipe_bytes": RECIPE + b" "})


def test_malformed_receipt_fails_replay():
    assert replay_receipt([], **INPUTS) == (False, "INVALID_RECEIPT_SHAPE")
    assert replay_receipt(None, **INPUTS) == (False, "INVALID_RECEIPT_SHAPE")


def test_cli_writes_and_replays_receipt_then_rejects_false_ok(tmp_path):
    path = tmp_path / "receipt.json"
    args = ("--intent", FIX / "intent-aicr-synthetic.json",
            "--recipe", FIX / "aicr-recipe-result-synthetic.json",
            "--expected-recipe-sha256", PIN,
            "--aibom", FIX / "aibom-v1beta1-synthetic.json", "--now", NOW)
    created = invoke("receipt-offline", *args, "--output", path)
    assert created.returncode == 0, created.stderr
    assert json.loads(created.stdout)["status"] == "UNKNOWN"
    checked = invoke("replay-offline", *args, "--receipt", path)
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["verified_replay"] is True
    forged = json.loads(path.read_text())
    forged["decision"]["status"] = "OK"
    path.write_text(json.dumps(forged))
    rejected = invoke("replay-offline", *args, "--receipt", path)
    assert rejected.returncode == 2, rejected.stderr
    assert json.loads(rejected.stdout)["verified_replay"] is False


def test_cli_source_reencoding_rejected_after_receipt(tmp_path):
    receipt_file = tmp_path / "receipt.json"
    adapted = (tmp_path / "aibom.json")
    adapted.write_bytes(AIBOM)
    args = ("--intent", FIX / "intent-aicr-synthetic.json",
            "--recipe", FIX / "aicr-recipe-result-synthetic.json",
            "--expected-recipe-sha256", PIN, "--aibom", adapted, "--now", NOW)
    assert invoke("receipt-offline", *args, "--output", receipt_file).returncode == 0
    adapted.write_bytes(AIBOM + b"\n")
    checked = invoke("replay-offline", *args, "--receipt", receipt_file)
    assert checked.returncode == 2
    assert json.loads(checked.stdout)["reason"] == "RECEIPT_CONTRADICTS_RAW_SOURCES"


def test_cli_never_overwrites_existing_checkpoint_or_evidence_file(tmp_path):
    path = tmp_path / "previous-receipt.json"
    path.write_text("DO NOT TOUCH", encoding="utf-8")
    args = ("--intent", FIX / "intent-aicr-synthetic.json",
            "--recipe", FIX / "aicr-recipe-result-synthetic.json",
            "--expected-recipe-sha256", PIN,
            "--aibom", FIX / "aibom-v1beta1-synthetic.json", "--now", NOW)
    result = invoke("receipt-offline", *args, "--output", path)
    assert result.returncode == 3
    assert path.read_text(encoding="utf-8") == "DO NOT TOUCH"
