from dataclasses import replace
import pytest
from runtime_assurance_lab.contracts import Intent, Observation, timestamp
from runtime_assurance_lab.bench import dataset


def test_strict_normalized_contracts():
    intent, observation, *_ = next(dataset(1))
    assert Intent.parse({k: getattr(intent, k) for k in intent.__dataclass_fields__}) == intent
    record = {k: getattr(observation, k) for k in observation.__dataclass_fields__}
    record["observed_at"] = observation.observed_at.isoformat()
    assert Observation.parse(record) == observation


@pytest.mark.parametrize('field,value',[
    ('workload','../escape'), ('model_digest','sha256:hello'),
    ('image_digest','sha256:'+'a'*63), ('platform_recipe_digest','SHA256:'+'a'*64),
    ('model_ref',''), ('workload','lab/foo/bar')])
def test_bad_intent_rejected(field,value):
    intent, *_ = next(dataset(1))
    data={k:getattr(intent,k) for k in intent.__dataclass_fields__}
    data[field]=value
    with pytest.raises(ValueError): Intent.parse(data)


def test_unknown_field_rejected():
    intent, *_ = next(dataset(1))
    data={k:getattr(intent,k) for k in intent.__dataclass_fields__}
    data['access_token']='no-thanks'
    with pytest.raises(ValueError): Intent.parse(data)


@pytest.mark.parametrize('s', ['2026-11-12T03:25:00', 'not-a-time', '', 1700])
def test_untrusted_timestamps_fail(s):
    with pytest.raises(ValueError): timestamp(s)


def test_null_identity_does_not_pass():
    from datetime import timezone
    from runtime_assurance_lab.evaluate import evaluate
    from runtime_assurance_lab.bench import FIXED_NOW
    intent, observation, *_ = next(dataset(1))
    outcome=evaluate(intent, replace(observation,model_digest=None),now=FIXED_NOW)
    assert outcome.status == 'UNKNOWN'
