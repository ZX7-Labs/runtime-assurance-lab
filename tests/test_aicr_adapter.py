"""Pinned AICR v1.2.0 RecipeResult adapter, fully synthetic; no live GPU or API."""
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from runtime_assurance_lab.aicr_adapter import pin_recipe, SOURCE_VERSION
from runtime_assurance_lab.contracts import Intent
from test_integration_performance import invoke

ROOT = Path(__file__).resolve().parents[1]
RECIPE = (ROOT / 'fixtures/aicr-recipe-result-synthetic.json').read_bytes()
RAW = json.loads(RECIPE)
INTENT = Intent.parse(json.loads((ROOT / 'fixtures/intent-aicr-synthetic.json').read_text()))
PIN = INTENT.platform_recipe_digest


def test_exact_bytes_pin_with_explicit_trust_limitations():
    r = pin_recipe(RECIPE, PIN, INTENT)
    assert r.source_version == SOURCE_VERSION
    assert r.sha256 == PIN
    assert r.component_names == ('gpu-operator',)
    assert r.intent_category == 'inference'
    assert 'AICR_RECIPE_NOT_DEPLOYMENT_PROOF' in r.limitations
    assert 'AICR_RECIPE_NOT_ATTESTED' in r.limitations


def test_whitespace_reencoding_changes_exact_bytes_and_fails():
    with pytest.raises(ValueError, match='pinned digest'):
        pin_recipe(RECIPE + b' ', PIN, INTENT)


def test_pinned_digest_must_match_separate_intent():
    with pytest.raises(ValueError, match='intent'):
        pin_recipe(RECIPE, 'sha256:' + '0' * 64, INTENT)


def test_bad_pin_rejected():
    with pytest.raises(ValueError, match='digest'):
        pin_recipe(RECIPE, 'not-a-digest', INTENT)


def test_file_size_bound_and_invalid_utf8():
    with pytest.raises(ValueError, match='bounded'):
        pin_recipe(b'', PIN, INTENT)
    with pytest.raises(ValueError, match='bounded'):
        pin_recipe(b'x' * (8 * 1024 * 1024 + 1), PIN, INTENT)
    invalid = b'\xff\xfe'
    intent = _intent_for(invalid)
    with pytest.raises(ValueError, match='UTF-8'):
        pin_recipe(invalid, intent.platform_recipe_digest, intent)


def _intent_for(raw):
    data = json.loads((ROOT / 'fixtures/intent-aicr-synthetic.json').read_text())
    data['platform_recipe_digest'] = 'sha256:' + sha256(raw).hexdigest()
    return Intent.parse(data)


def _pin_invalid(raw):
    intent = _intent_for(raw)
    return pin_recipe(raw, intent.platform_recipe_digest, intent)


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(apiVersion='aicr.run/v1beta1'),
    lambda d: d.update(kind='RecipeMetadata'),
    lambda d: d.pop('componentRefs'),
    lambda d: d.update(componentRefs={}),
    lambda d: d['componentRefs'][0].pop('source'),
    lambda d: d['componentRefs'].append(deepcopy(d['componentRefs'][0])),
    lambda d: d.update(criteria='inference'),
    lambda d: d.update(criteria={'intent':'unsupported'}),
    lambda d: d.update(criteria={'nodes':True}),
    lambda d: d.update(deploymentOrder=['gpu-operator', 'gpu-operator']),
    lambda d: d.update(metadata=[]),
])
def test_invalid_and_ambiguous_recipe_fields_fail_closed(mutation):
    data = deepcopy(RAW)
    mutation(data)
    with pytest.raises(ValueError):
        _pin_invalid(json.dumps(data).encode())


def test_duplicate_keys_and_nonfinite_rejected_even_with_correct_pin():
    for raw in (b'{"kind":"RecipeResult","kind":"RecipeResult"}',
                b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'):
        with pytest.raises(ValueError):
            _pin_invalid(raw)


def test_nulls_report_missing_coverage_without_fabricated_components():
    data = deepcopy(RAW)
    data['criteria'] = None
    data['componentRefs'] = None
    data['deploymentOrder'] = None
    r = _pin_invalid(json.dumps(data).encode())
    assert r.component_names == ()
    assert 'AICR_CRITERIA_UNSPECIFIED' in r.limitations
    assert 'AICR_COMPONENT_REFS_EMPTY' in r.limitations


def test_cli_combines_pinned_recipe_and_aibom_but_remains_unknown():
    p = invoke('correlate-offline', '--intent', ROOT/'fixtures/intent-aicr-synthetic.json',
               '--recipe', ROOT/'fixtures/aicr-recipe-result-synthetic.json',
               '--expected-recipe-sha256', PIN,
               '--aibom', ROOT/'fixtures/aibom-v1beta1-synthetic.json',
               '--now', '2026-11-12T03:25:00Z')
    assert p.returncode == 2, p.stderr
    result = json.loads(p.stdout)
    assert result['status'] == 'UNKNOWN'
    assert 'MODEL_DIGEST_UNRESOLVED' in result['rules']
    assert result['sources']['aicr']['sha256'] == PIN
    assert 'AICR_RECIPE_NOT_DEPLOYMENT_PROOF' in result['sources']['aicr']['limitations']
    assert 'MODEL_SIGNATURE_NOT_INDEPENDENTLY_VERIFIED' in result['sources']['aibom']['limitations']


def test_cli_tampered_recipe_returns_invalid_without_decision(tmp_path):
    changed = tmp_path/'tampered.json'
    changed.write_bytes(RECIPE + b' ')
    p = invoke('correlate-offline', '--intent', ROOT/'fixtures/intent-aicr-synthetic.json',
               '--recipe', changed, '--expected-recipe-sha256', PIN,
               '--aibom', ROOT/'fixtures/aibom-v1beta1-synthetic.json',
               '--now', '2026-11-12T03:25:00Z')
    assert p.returncode == 3
    assert not p.stdout
    assert 'pinned digest' in p.stderr



def test_upstream_compatible_empty_source_with_local_manifest_keeps_trust_limit():
    """The pinned NVIDIA v1.2.0 repo carries legitimate local manifests."""
    data = deepcopy(RAW)
    comp = data['componentRefs'][0]
    comp['source'] = ''
    comp['manifestFiles'] = ['components/custom/manifests/local.yaml']
    result = _pin_invalid(json.dumps(data).encode())
    assert result.component_names == ('gpu-operator',)
    assert 'AICR_LOCAL_MANIFEST_SOURCE_UNATTESTED' in result.limitations
    assert 'AICR_RECIPE_NOT_ATTESTED' in result.limitations


@pytest.mark.parametrize('manifest', [None, [], 'not-a-list', [123], [''], ['  '], ['x' * 501]])
def test_empty_source_without_valid_local_manifest_fails(manifest):
    data = deepcopy(RAW)
    data['componentRefs'][0]['source'] = ''
    if manifest is not None:
        data['componentRefs'][0]['manifestFiles'] = manifest
    with pytest.raises(ValueError, match='local manifestFiles'):
        _pin_invalid(json.dumps(data).encode())
