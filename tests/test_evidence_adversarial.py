from copy import deepcopy
import pytest
from runtime_assurance_lab.evidence import append, canonical, generate_signer, head, sha, verify


def build_log():
    keys={kind:generate_signer() for kind in ('intent','observation','decision')}
    trust={kind:(keys[kind][1],kind) for kind in keys}
    log=[]
    a=append(log,'intent',{'workload':'lab/a','model_ref':'hf://approved'},[], 'intent', keys['intent'][0])
    b=append(log,'observation',{'workload':'lab/a','model_ref':'hf://approved'},[], 'observation',keys['observation'][0])
    append(log,'decision',{'workload':'lab/a','status':'OK'},[sha(canonical(a)),sha(canonical(b))], 'decision',keys['decision'][0])
    return log, trust, keys


def anchored_verify(log, trust, anchor):
    return verify(log,trust,expected_head=anchor[0],expected_count=anchor[1])


def test_signed_causal_chain():
    log,trust,_=build_log()
    assert anchored_verify(log,trust,(head(log),len(log)))==(True,'VERIFIED_LOCAL_CHAIN')


@pytest.mark.parametrize('attack', ['payload','signature','reorder','omit_middle','truncate_tail','wrong_role','bad_ref','wrong_workload','unknown_signer','duplicate_ref'])
def test_adversarial_attacks_rejected(attack):
    log,trust,_=build_log()
    anchor=(head(log),len(log))
    forged=deepcopy(log)
    if attack=='payload': forged[1]['payload']['model_ref']='hf://malicious'
    if attack=='signature': forged[1]['signature']='AA=='
    if attack=='reorder': forged[0],forged[1]=forged[1],forged[0]
    if attack=='omit_middle': forged.pop(1)
    if attack=='truncate_tail': forged.pop()
    if attack=='wrong_role': forged[1]['kind']='intent'
    if attack=='bad_ref': forged[2]['refs'][0]='f'*64
    if attack=='wrong_workload': forged[2]['payload']['workload']='lab/b'
    if attack=='unknown_signer': forged[1]['signer_id']='suspicious'
    if attack=='duplicate_ref': forged[2]['refs']=[forged[2]['refs'][0]]*2
    ok,_=anchored_verify(forged,trust,anchor)
    assert not ok


def test_wrong_trust_root_rejected():
    log,trust,_=build_log()
    _,bad_pub=generate_signer()
    bad_trust=deepcopy(trust)
    bad_trust['observation']=(bad_pub,'observation')
    assert not anchored_verify(log,bad_trust,(head(log),len(log)))[0]


def test_anchor_missing_raises_type_error():
    log,trust,_=build_log()
    with pytest.raises(TypeError): verify(log,trust,expected_count=len(log))


def test_validly_signed_wrong_workload_decision_fails_semantic_binding():
    log,trust,keys=build_log()
    log.pop()
    refs=[sha(canonical(log[0])),sha(canonical(log[1]))]
    append(log,'decision',{'workload':'lab/b','status':'OK'},refs,'decision',keys['decision'][0])
    ok, reason=anchored_verify(log,trust,(head(log),len(log)))
    assert not ok and reason=='DECISION_WORKLOAD_MISBOUND'


def test_provenance_authorization_prevents_observer_spoofing_intent():
    log,trust,keys=build_log()
    log=[]
    append(log,'intent',{'workload':'lab/a'},[],'observation',keys['observation'][0])
    ok,reason=anchored_verify(log,trust,(head(log),1))
    assert not ok and reason=='UNAUTHORIZED_SIGNER_OR_KIND'


def test_valid_signed_but_false_decision_rejected_by_independent_recomputation():
    from runtime_assurance_lab.bench import dataset, FIXED_NOW
    from runtime_assurance_lab.evidence import verify_decision_semantics
    from dataclasses import asdict
    from runtime_assurance_lab.evaluate import POLICY_VERSION
    intent, ob, _, _ = next(x for x in dataset(1) if x[3]=='model_digest')
    keys={kind:generate_signer() for kind in ('intent','observation','decision')}
    trust={kind:(keys[kind][1],kind) for kind in keys}
    events=[]
    a=append(events,'intent',asdict(intent),[],'intent',keys['intent'][0])
    obs_payload=asdict(ob)
    obs_payload['observed_at']=ob.observed_at.isoformat()
    b=append(events,'observation',obs_payload,[],'observation',keys['observation'][0])
    # A fully authorized evaluator signs a false assertion: crypto alone is insufficient.
    append(events,'decision',{'workload':intent.workload,'status':'OK','rules':[],
           'policy_version':POLICY_VERSION,'evaluated_at':FIXED_NOW.isoformat()},
           [sha(canonical(a)),sha(canonical(b))],'decision',keys['decision'][0])
    assert anchored_verify(events,trust,(head(events),len(events)))[0]
    valid,reason=verify_decision_semantics(events,trusted_now=FIXED_NOW.isoformat())
    assert not valid and reason=='DECISION_CONTRADICTS_EVIDENCE'


def test_invalid_reference_element_does_not_crash():
    log,trust,_=build_log()
    anchor=(head(log),len(log))
    log[2]['refs']=[['unhashable']]
    valid,reason=anchored_verify(log,trust,anchor)
    assert not valid and reason=='INVALID_REFERENCES'


def test_signed_decision_clock_replay_rejected():
    from runtime_assurance_lab.evidence import verify_decision_semantics
    from runtime_assurance_lab.cli import demo
    from pathlib import Path
    import tempfile,json
    with tempfile.TemporaryDirectory() as directory:
        out=Path(directory)
        demo(Path(__file__).parents[1]/'fixtures',out)
        log=json.loads((out/'journal.json').read_text())
        valid,reason=verify_decision_semantics(log,trusted_now='2026-11-12T03:25:01+00:00')
        assert not valid and reason=='UNTRUSTED_POLICY_OR_CLOCK'


@pytest.mark.parametrize('bad_trust', [None, [], 'not-a-map', 123])
def test_invalid_trust_container_fails_closed(bad_trust):
    log, _, _=build_log()
    assert anchored_verify(log,bad_trust,(head(log),len(log))) == (False,'INVALID_INPUT')

@pytest.mark.parametrize('bad_head', [None, '', 123, 'G'*64, 'a'*63])
def test_invalid_external_anchor_fails_closed(bad_head):
    log, trust, _=build_log()
    assert anchored_verify(log,trust,(bad_head,len(log))) == (False,'INVALID_INPUT')


def test_validly_signed_decision_cannot_insert_extra_assurance_claims():
    from runtime_assurance_lab.cli import demo
    from runtime_assurance_lab.evidence import verify_decision_semantics
    from pathlib import Path
    import json, tempfile
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory)
        demo(Path(__file__).parents[1]/'fixtures', out)
        events = json.loads((out/'journal.json').read_text())
        # A malicious/compromised authorized decision signer could sign extra fields.
        events[2]['payload']['production_ready'] = True
        ok, reason = verify_decision_semantics(events, trusted_now='2026-11-12T03:25:00+00:00')
        assert (ok, reason) == (False, 'UNEXPECTED_DECISION_FIELDS')
