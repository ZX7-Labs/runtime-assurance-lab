"""AIBOM adapter tests: all resources are synthetic, not exported from clusters."""
from copy import deepcopy
from hashlib import sha256
import base64
import json
from pathlib import Path
import pytest

from runtime_assurance_lab.aibom_adapter import SOURCE_VERSION, normalize_aibom
from runtime_assurance_lab.contracts import Intent, timestamp
from runtime_assurance_lab.evaluate import evaluate
from test_integration_performance import invoke

ROOT = Path(__file__).resolve().parents[1]
SOURCE = json.loads((ROOT / 'fixtures/aibom-v1beta1-synthetic.json').read_text())
INTENT = Intent.parse(json.loads((ROOT / 'fixtures/intent.json').read_text()))
NOW = timestamp('2026-11-12T03:25:00Z')


def test_pinned_v1beta1_adapter_never_promotes_claim_to_verified_ok():
    result = normalize_aibom(SOURCE)
    assert result.source_version == SOURCE_VERSION
    assert result.observation.workload == INTENT.workload
    assert result.observation.model_ref == INTENT.model_ref
    assert result.observation.model_confidence == 'declared'
    assert result.observation.model_digest is None
    assert 'MODEL_SIGNATURE_NOT_INDEPENDENTLY_VERIFIED' in result.limitations
    finding = evaluate(INTENT, result.observation, now=NOW)
    assert finding.status == 'UNKNOWN'
    assert 'MODEL_DIGEST_UNRESOLVED' in finding.rules


@pytest.mark.parametrize('mutation,reason', [
    (lambda x: x['status']['conditions'][0].update(status='False'), 'AIBOM_NOT_READY'),
    (lambda x: x['status']['conditions'][1].update(status='True'), 'AIBOM_SOURCE_STALE'),
    (lambda x: x['status'].update(observedGeneration=0), 'AIBOM_GENERATION_NOT_OBSERVED'),
    (lambda x: x['status'].pop('lastReconciled'), 'AIBOM_LAST_RECONCILED_MISSING'),
    (lambda x: x['status'].pop('summary'), 'AIBOM_SUMMARY_MISSING'),
])
def test_unhealthy_or_incomplete_aibom_has_no_usable_observation(mutation, reason):
    source = deepcopy(SOURCE)
    mutation(source)
    result = normalize_aibom(source)
    assert result.observation is None
    assert reason in result.limitations
    assert evaluate(INTENT, result.observation, now=NOW).status == 'UNKNOWN'


@pytest.mark.parametrize('mutation', [
    lambda x: x.update(apiVersion='aibom.k8saibom.dev/v1alpha1'),
    lambda x: x['status']['summary']['workload'].update(namespace='other'),
    lambda x: x['status']['summary']['workload'].update(name='different'),
    lambda x: x['spec'].update(bomSpecVersion='1.5'),
    lambda x: x['status']['conditions'].append({'type':'Ready','status':'True'}),
    lambda x: x['status']['bomDocument']['inline'].update(data='!!bad-base64'),
    lambda x: x['status']['bomDocument'].update(sha256='f'*64),
    lambda x: x['status']['bomDocument'].update(size=1),
    lambda x: x['status']['bomDocument'].update(external={'sink':'webhook','writeOnly':True}),
    lambda x: x['status']['summary']['models'][0].update(confidence='verified'),
])
def test_schema_mismatch_and_inline_corruption_fail_closed(mutation):
    source = deepcopy(SOURCE)
    mutation(source)
    with pytest.raises(ValueError):
        normalize_aibom(source)


def test_conflicting_model_identities_are_unresolved_not_selected_by_order():
    source = deepcopy(SOURCE)
    source['status']['summary']['models'].append({'identity':'hf://unexpected','confidence':'declared'})
    result = normalize_aibom(source)
    assert result.observation.model_ref is None
    assert 'MULTIPLE_MODEL_IDENTITIES' in result.limitations
    assert evaluate(INTENT, result.observation, now=NOW).status == 'UNKNOWN'


def test_external_write_only_bom_is_not_fetched_or_trusted():
    source = deepcopy(SOURCE)
    doc = source['status']['bomDocument']
    doc.pop('inline')
    doc['external'] = {'sink':'webhook','url':'https://example.invalid/fixture','writeOnly':True}
    result = normalize_aibom(source)
    assert 'EXTERNAL_BOM_NOT_RETRIEVED' in result.limitations
    assert evaluate(INTENT, result.observation, now=NOW).status == 'UNKNOWN'


def test_cli_evaluate_aibom_returns_machine_readable_unknown():
    result = invoke('evaluate-aibom','--intent',ROOT/'fixtures/intent.json','--aibom',
                    ROOT/'fixtures/aibom-v1beta1-synthetic.json','--now','2026-11-12T03:25:00Z')
    assert result.returncode == 2, result.stderr
    body = json.loads(result.stdout)
    assert body['status'] == 'UNKNOWN'
    assert body['adapter']['source_version'] == SOURCE_VERSION


def test_cli_schema_mismatch_exits_invalid(tmp_path):
    source = deepcopy(SOURCE)
    source['apiVersion'] = 'not-valid/v9'
    p = tmp_path/'bad.json'
    p.write_text(json.dumps(source))
    result = invoke('evaluate-aibom','--intent',ROOT/'fixtures/intent.json','--aibom',p,
                    '--now','2026-11-12T03:25:00Z')
    assert result.returncode == 3


def test_invalid_condition_type_fails_closed_without_unhandled_type_error():
    source = deepcopy(SOURCE)
    source['status']['conditions'][0]['type'] = ['invalid-unhashable']
    with pytest.raises(ValueError, match='condition type'):
        normalize_aibom(source)


def test_valid_checksum_does_not_make_nonsense_a_valid_bom():
    source = deepcopy(SOURCE)
    raw = b'{"bomFormat":"not-CycloneDX", "specVersion":"1.6"}'
    doc = source['status']['bomDocument']
    doc['inline']['data'] = base64.b64encode(raw).decode('ascii')
    doc['size'] = len(raw)
    doc['sha256'] = sha256(raw).hexdigest()
    source['status']['bomHash'] = doc['sha256']
    with pytest.raises(ValueError, match='not supported CycloneDX'):
        normalize_aibom(source)


def test_inline_bom_exponent_overflow_rejected_even_with_valid_hash():
    source = deepcopy(SOURCE)
    raw = b'{"bomFormat":"CycloneDX","specVersion":"1.6","components":[{"risk":1e999}]}'
    doc = source['status']['bomDocument']
    doc['inline']['data'] = base64.b64encode(raw).decode('ascii')
    doc['size'] = len(raw)
    doc['sha256'] = sha256(raw).hexdigest()
    source['status']['bomHash'] = doc['sha256']
    with pytest.raises(ValueError, match='nonfinite'):
        normalize_aibom(source)
