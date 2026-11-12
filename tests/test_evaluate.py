from dataclasses import replace
from datetime import timedelta
import pytest
from runtime_assurance_lab.bench import dataset, FIXED_NOW, d
from runtime_assurance_lab.evaluate import evaluate, _evaluate_authenticated_claims


def test_all_known_scenarios():
    expected={'clean':'OK','model_ref':'DRIFT','model_digest':'DRIFT','image_digest':'DRIFT',
              'platform_recipe_digest':'DRIFT','stale':'STALE','missing':'UNKNOWN',
              'unverified':'UNKNOWN','unresolved':'UNKNOWN','future':'UNKNOWN'}
    for intent, ob, label, case in dataset(2):
        result=_evaluate_authenticated_claims(intent, ob, now=FIXED_NOW)
        assert result.status == expected[case]
        assert bool(result.status!='OK') == label


def test_freshness_boundaries_are_inclusive():
    intent, ob, *_ = next(dataset(1))
    assert _evaluate_authenticated_claims(intent, replace(ob,observed_at=FIXED_NOW-timedelta(seconds=300)),now=FIXED_NOW).status=='OK'
    assert _evaluate_authenticated_claims(intent, replace(ob,observed_at=FIXED_NOW-timedelta(seconds=300,microseconds=1)),now=FIXED_NOW).status=='STALE'
    assert _evaluate_authenticated_claims(intent, replace(ob,observed_at=FIXED_NOW+timedelta(seconds=30)),now=FIXED_NOW).status=='OK'
    assert _evaluate_authenticated_claims(intent, replace(ob,observed_at=FIXED_NOW+timedelta(seconds=30,microseconds=1)),now=FIXED_NOW).status=='UNKNOWN'


def test_stale_mismatch_does_not_claim_current_drift():
    intent, ob, *_ = next(dataset(1))
    ob=replace(ob,model_ref='hf://evil',observed_at=FIXED_NOW-timedelta(minutes=6))
    outcome=_evaluate_authenticated_claims(intent,ob,now=FIXED_NOW)
    assert outcome.status=='STALE'
    assert 'MODEL_REF_MISMATCH' not in outcome.rules


def test_unverified_mismatch_is_nevertheless_a_declared_conflict():
    intent, ob, *_ = next(dataset(1))
    result=_evaluate_authenticated_claims(intent,replace(ob,model_confidence='declared', model_digest=d('rogue')),now=FIXED_NOW)
    assert result.status=='DRIFT'
    assert 'MODEL_NOT_CRYPTO_VERIFIED' in result.rules


def test_wrong_workload_binding_and_now_validation():
    intent, ob, *_ = next(dataset(1))
    assert _evaluate_authenticated_claims(intent,replace(ob,workload='lab/other'),now=FIXED_NOW).status=='UNKNOWN'
    with pytest.raises(ValueError): _evaluate_authenticated_claims(intent, ob, now=FIXED_NOW.replace(tzinfo=None))
    with pytest.raises(ValueError): _evaluate_authenticated_claims(intent, ob, now=FIXED_NOW, max_age_seconds=0)


def test_untrusted_complete_matching_or_mismatching_claims_fail_closed():
    intent, ob, *_ = next(dataset(1))
    for observation in (ob, replace(ob, model_digest=d('forged-model'))):
        result = evaluate(intent, observation, now=FIXED_NOW)
        assert result.status == 'UNKNOWN'
        assert result.rules == ('SOURCE_AUTHENTICITY_UNVERIFIED',)
