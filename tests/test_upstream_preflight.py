"""Independently constructed public-testdata controls: never invoke network."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
import subprocess
import sys

import pytest

from runtime_assurance_lab.upstream_preflight import (
    DECISION, MAX_SOURCE_BYTES, PINS, SourcePin, analyze_public_upstream_fixtures,
    download_public_fixtures, git_blob_sha1, inspect_google_bom, verify_source_bytes,
)


def _serial(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pin(key, raw):
    return SourcePin(key, "TEST/fake", "a" * 40, f"{key}.json", git_blob_sha1(raw), len(raw))


@pytest.fixture
def sample():
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.6",
           "metadata": {"timestamp": "2026-05-10T12:00:00Z",
                        "component": {"properties": [
                            {"name": f"aibom.workload.{k}", "value": v}
                            for k, v in (("name", "vllm-llama3"), ("namespace", "prod-inference"),
                                         ("kind", "Deployment"), ("group", "apps"), ("category", "inference"))]}},
           "components": [
               {"type": "container", "name": "container",
                "hashes": [{"alg": "SHA-256", "content": "1" * 64}]},
               {"type": "machine-learning-model", "name": "meta-llama/model",
                "properties": [{"name": "aibom.confidence", "value": "declared"},
                               {"name": "aibom.evidence.locator", "value": "args[0]"}]},
               {"type": "machine-learning-model", "name": "meta-llama/model",
                "properties": [{"name": "aibom.confidence", "value": "inferred"}]},
           ]}
    recipe = {"kind": "RecipeResult", "apiVersion": "aicr.run/v1",
              "metadata": {"version": "1.1.2"},
              "criteria": {"intent": "training", "service": "eks", "accelerator": "h100"},
              "componentRefs": [{"name": "gpu-operator", "source": "repo", "type": "helm"}],
              "deploymentOrder": ["gpu-operator"]}
    return bom, recipe


def _derive(sample):
    bom, recipe = sample
    raw = {"google_bom": _serial(bom), "nvidia_recipe": _serial(recipe)}
    return raw, (_pin("google_bom", raw["google_bom"]), _pin("nvidia_recipe", raw["nvidia_recipe"]))


def test_real_source_pins_are_immutable_commit_paths():
    assert len(PINS) == 2
    assert len({p.key for p in PINS}) == 2
    for p in PINS:
        assert p.raw_url.startswith("https://raw.githubusercontent.com/")
        assert len(p.commit) == len(p.git_blob_sha1) == 40
        assert p.size_bytes <= MAX_SOURCE_BYTES
        assert f"/{p.commit}/" in p.raw_url


def test_empty_and_invalid_raw_inputs_fail_closed(sample):
    raw, pins = _derive(sample)
    for malformed in ["", "[]", "null", "{\"x\":NaN}", "{\"x\":1,\"x\":2}"]:
        blob = malformed.encode()
        with pytest.raises(ValueError):
            verify_source_bytes(blob, _pin("google_bom", blob))
    with pytest.raises(ValueError):
        verify_source_bytes(b"x" * (MAX_SOURCE_BYTES + 1), _pin("google_bom", b"x" * (MAX_SOURCE_BYTES + 1)))


def test_mutated_bytes_rejected_even_if_semantically_equivalent(sample):
    raw, pins = _derive(sample)
    original = raw["google_bom"]
    verify_source_bytes(original, pins[0])
    for tampered in (original + b"\n", original.replace(b'"CycloneDX"', b'"SPDX"')):
        with pytest.raises(ValueError, match="pinned Git object"):
            verify_source_bytes(tampered, pins[0])


def test_identity_hash_is_git_blob_format():
    raw = b"abc"
    assert git_blob_sha1(raw) == sha1(b"blob 3\x00abc").hexdigest()


def test_reference_probe_never_claims_product_value(sample):
    raw, pins = _derive(sample)
    result = analyze_public_upstream_fixtures(raw, pins=pins)
    assert result["decision"] == DECISION
    assert result["upstream_binaries_executed"] is False
    assert result["authentic_runtime_assurance"] is False
    assert not result["cross_plane_link_verified"]
    assert not result["independently_demonstrated_incremental_signal"]
    assert result["baseline_existing_google"]["component_count"] == 3
    assert result["baseline_existing_google"]["model_claim_components"] == 2
    assert result["baseline_existing_google"]["distinct_model_names"] == ["meta-llama/model"]
    assert result["baseline_existing_google"]["image_sha256_claims"] == ["sha256:" + "1" * 64]
    assert result["nvidia_recipe"]["component_count"] == 1
    assert result["nvidia_recipe"]["category"] == "training"
    assert result["aibom_adapter_probe"]["image_digest_in_normalized_observation"] is False
    assert result["aibom_adapter_probe"]["image_digest_in_original_bom"] is True
    assert len(result["sources"]) == 2
    assert all("sha256" in v and "commit" in v for v in result["sources"])


@pytest.mark.parametrize("drop", ["google_bom", "nvidia_recipe"])
def test_one_upstream_source_missing_blocks_study(sample, drop):
    raw, pins = _derive(sample)
    raw.pop(drop)
    with pytest.raises(ValueError, match="both exact"):
        analyze_public_upstream_fixtures(raw, pins=pins)


def test_extra_source_blocks_study(sample):
    raw, pins = _derive(sample)
    raw["attacker_source"] = raw["google_bom"]
    with pytest.raises(ValueError):
        analyze_public_upstream_fixtures(raw, pins=pins)


@pytest.mark.parametrize("mutate", [
    lambda bom: bom.update(bomFormat="SPDX"),
    lambda bom: bom.update(specVersion="1.5"),
    lambda bom: bom.update(components=[]),
    lambda bom: bom["metadata"].pop("component"),
    lambda bom: bom["metadata"]["component"]["properties"].pop(0),
    lambda bom: bom["components"][0]["hashes"][0].update(content="wrong"),
    lambda bom: bom["components"][1]["properties"][0].update(value="verified"),
    lambda bom: bom["components"][1].update(name=""),
    lambda bom: bom["metadata"]["component"]["properties"].append({"name":"aibom.workload.name", "value":"attacker"}),
])
def test_incompatible_google_bom_fails_analysis(sample, mutate):
    bom, recipe = deepcopy(sample)
    mutate(bom)
    raw, pins = _derive((bom, recipe))
    with pytest.raises(ValueError):
        analyze_public_upstream_fixtures(raw, pins=pins)


@pytest.mark.parametrize("mutate", [
    lambda recipe: recipe.update(kind="RecipeMetadata"),
    lambda recipe: recipe.update(apiVersion="aicr.run/v1beta1"),
    lambda recipe: recipe.update(componentRefs=[]),
    lambda recipe: recipe["componentRefs"].append(deepcopy(recipe["componentRefs"][0])),
])
def test_incompatible_or_unhelpful_recipe_fails_analysis(sample, mutate):
    bom, recipe = deepcopy(sample)
    mutate(recipe)
    raw, pins = _derive((bom, recipe))
    if not recipe["componentRefs"]:
        # AICR can have zero components, but this test deliberately checks
        # the preflight's inference limitations rather than a malformed file.
        result = analyze_public_upstream_fixtures(raw, pins=pins)
        assert result["nvidia_recipe"]["component_count"] == 0
    else:
        with pytest.raises(ValueError):
            analyze_public_upstream_fixtures(raw, pins=pins)


def test_aligned_categories_must_be_reviewed_not_assumed_joinable(sample):
    bom, recipe = deepcopy(sample)
    recipe["criteria"]["intent"] = "inference"
    raw, pins = _derive((bom, recipe))
    with pytest.raises(ValueError, match="matching intents"):
        analyze_public_upstream_fixtures(raw, pins=pins)


class _FakeResponse:
    def __init__(self, url, content, *, url_override=None, code=200):
        self._url, self._content, self._url_override, self._code = url, content, url_override, code
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def geturl(self): return self._url_override or self._url
    def getcode(self): return self._code
    def read(self, length): return self._content[:length]


class _FakeOpener:
    def __init__(self, assets, *, bad_url=None, code=200):
        self.assets, self.bad_url, self.code, self.visited = assets, bad_url, code, []
    def open(self, url, *, timeout):
        assert timeout <= 15
        self.visited.append(url)
        return _FakeResponse(url, self.assets[url], url_override=self.bad_url, code=self.code)


def test_download_only_uses_two_pinned_public_sources(sample, monkeypatch):
    raw, pins = _derive(sample)
    monkeypatch.setattr("runtime_assurance_lab.upstream_preflight.PINS", pins)
    opener = _FakeOpener({pin.raw_url: raw[pin.key] for pin in pins})
    got = download_public_fixtures(opener=opener)
    assert got == raw
    assert opener.visited == [p.raw_url for p in pins]


@pytest.mark.parametrize("tamper", ["redirect", "wrong_code", "wrong_bytes"])
def test_download_fails_closed_on_network_identity_failure(sample, monkeypatch, tamper):
    raw, pins = _derive(sample)
    monkeypatch.setattr("runtime_assurance_lab.upstream_preflight.PINS", pins)
    urls = {pin.raw_url: raw[pin.key] for pin in pins}
    if tamper == "wrong_bytes":
        urls[pins[0].raw_url] += b" "
    opener = _FakeOpener(urls, bad_url="https://other.invalid/" if tamper == "redirect" else None,
                         code=404 if tamper == "wrong_code" else 200)
    with pytest.raises(ValueError):
        download_public_fixtures(opener=opener)


def test_no_implicit_network_in_cli():
    p = subprocess.run([sys.executable, "scripts/run_upstream_preflight.py"],
                       text=True, capture_output=True, timeout=10)
    assert p.returncode == 2
    p = subprocess.run([sys.executable, "scripts/run_upstream_preflight.py", "--list-pins"],
                       text=True, capture_output=True, timeout=10)
    assert p.returncode == 0, p.stderr
    assert len(json.loads(p.stdout)["pins"]) == 2
