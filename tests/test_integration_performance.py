import json
import pytest
import os
from pathlib import Path
import subprocess
import sys
from runtime_assurance_lab.bench import run
from runtime_assurance_lab.cli import read_json

ROOT=Path(__file__).resolve().parents[1]
ENV={**os.environ,'PYTHONPATH':str(ROOT/'src')}


def invoke(*args):
    return subprocess.run([sys.executable,'-m','runtime_assurance_lab.cli',*map(str,args)],cwd=ROOT,env=ENV,capture_output=True,text=True)


def test_cli_end_to_end_and_tampering(tmp_path):
    out=tmp_path/'run'
    demo=invoke('demo','--fixtures',ROOT/'fixtures','--output',out)
    assert demo.returncode==0,demo.stderr
    data=json.loads(demo.stdout)
    assert data['chain_verified'] is True
    verification=invoke('verify','--journal',out/'journal.json','--trust',out/'trust-public.json','--checkpoint',out/'checkpoint.json')
    assert verification.returncode==0, verification.stderr
    malicious=json.loads((out/'journal.json').read_text())
    malicious[1]['payload']['model_digest']='sha256:'+'a'*64
    (out/'malicious.json').write_text(json.dumps(malicious))
    failed=invoke('verify','--journal',out/'malicious.json','--trust',out/'trust-public.json','--checkpoint',out/'checkpoint.json')
    assert failed.returncode==2
    assert json.loads(failed.stdout)['verified'] is False


def test_cli_nonconformance_exit(tmp_path):
    clean=invoke('evaluate','--intent',ROOT/'fixtures/intent.json','--observation',ROOT/'fixtures/clean.json','--now','2026-11-12T03:25:00Z')
    assert clean.returncode==2,clean.stderr
    assert "SOURCE_AUTHENTICITY_UNVERIFIED" in clean.stdout
    mismatch=invoke('evaluate','--intent',ROOT/'fixtures/intent.json','--observation',ROOT/'fixtures/model-drift.json','--now','2026-11-12T03:25:00Z')
    assert mismatch.returncode==2
    assert 'SOURCE_AUTHENTICITY_UNVERIFIED' in mismatch.stdout


def test_synthetic_quality_and_benchmark_smoke():
    report=run(repetitions=6,loops=2)
    p=report['proposed']['classification']
    baseline=report['naive_local_comparator']['classification']
    assert p['recall'] == 1 and p['false_positive_rate']==0
    assert p['recall'] > baseline['recall']
    assert report['proposed']['microbench']['p95_us']>0
    assert report['crypto']['verify_ms']>0
    assert report['synthetic_event_to_verdict']['p95_us']>0


def test_json_boundary_rejects_duplicate_keys_nonfinite_and_excess_size(tmp_path):
    from runtime_assurance_lab.cli import MAX_JSON_BYTES, read_json
    import pytest
    for data in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"nested":{"b":1,"b":2}}'):
        path=tmp_path/'bad.json'
        path.write_text(data, encoding='utf-8')
        with pytest.raises(ValueError):
            read_json(path)
    invalid=tmp_path/'bad-utf8.json'
    invalid.write_bytes(b'\xff')
    with pytest.raises(UnicodeDecodeError):
        read_json(invalid)
    big=tmp_path/'large.json'
    big.write_bytes(b' '* (MAX_JSON_BYTES+1))
    with pytest.raises(ValueError, match='exceeds'):
        read_json(big)
    good=tmp_path/'good.json'
    good.write_text('{"b":2, "a":1}')
    assert read_json(good)=={'a':1, 'b':2}


def test_cli_invalid_ambiguous_json_fails_closed(tmp_path):
    ambiguous=tmp_path/'ambiguous.json'
    original=(ROOT/'fixtures/intent.json').read_text()
    assert original.lstrip().startswith('{')
    ambiguous.write_text('{"workload":"lab/one", "workload":"lab/two"}')
    result=invoke('evaluate','--intent',ambiguous,'--observation',ROOT/'fixtures/clean.json',
                  '--now','2026-11-12T03:25:00Z')
    assert result.returncode==3
    assert 'duplicate JSON key' in result.stderr


def test_strict_file_json_rejects_finite_exponent_overflow(tmp_path):
    source = tmp_path / 'overflow.json'
    source.write_text('{"nested":{"value":1e999}}', encoding='utf-8')
    with pytest.raises(ValueError, match='nonfinite'):
        read_json(source)
