import json
from types import SimpleNamespace

from scar_public.sentry_evidence import OutcomeLedger,LongContextActor,EvidenceJudge


def test_retrieval_retains_actual_old_outcome_beyond_window():
    ledger=OutcomeLedger()
    ledger.add(1,'pick up alloy','I picked up alloy.')
    ledger.add(2,'craft 1 blade','I successfully crafted 1 blade. It is now on the ground.')
    for i in range(3,20):ledger.add(i,'enter room','I entered room.')
    rows=ledger.retrieve('I used alloy to craft blade before.',before=15)
    assert {1,2}<={r['step'] for r in rows}
    assert all(r['step']<15 for r in rows)


def test_record_does_not_convert_attempt_to_success():
    ledger=OutcomeLedger();ledger.add(1,'craft 1 blade','Cannot craft blade: missing forge.')
    text,rows=ledger.context('blade forge',before=2)
    assert rows[0]['observation'].startswith('Cannot')
    assert 'action string alone does not show success' in text


def test_historical_holding_is_not_promoted_to_current_inventory():
    ledger=OutcomeLedger();ledger.add(1,'pick up token','I am holding 1 token.')
    text,_=ledger.context('token',2)
    assert 'not current inventory' in text and 'current feedback takes precedence' in text


def test_query_is_read_only_bounded_and_deduplicated():
    ledger=OutcomeLedger(limit=3,excerpt_chars=100)
    for i in range(30):ledger.add(i,'inspect token','token '+str(i)+'x'*200)
    before=json.dumps(ledger.records)
    rows=ledger.retrieve('token',30)
    assert len(rows)<=2 and all(len(r['observation'])<=100 and r['truncated'] for r in rows)
    assert json.dumps(ledger.records)==before


def test_cannot_append_duplicate_or_future_reordered_cycle():
    import pytest
    ledger=OutcomeLedger();ledger.add(3,'inspect token','Observed token.')
    with pytest.raises(ValueError):ledger.add(2,'inspect token','Observed token.')


def test_name_changes_do_not_change_retrieval_mechanism():
    for target in ('blade','artifact_z'):
        ledger=OutcomeLedger();ledger.add(0,'craft 1 '+target,'I successfully crafted 1 '+target)
        assert ledger.retrieve(target,1)[0]['step']==0


def test_clean_actor_has_no_extra_schema_or_scar_gate_and_retains_guidance():
    class Provider:
        def generate(self,prompt,system):
            self.prompt=prompt;self.system=system
            return dict(response=json.dumps(dict(reasoning='Actual reasoning',action='inspect token')))
    p=Provider();actor=LongContextActor(p,'system');actor.act('observation')
    assert p.prompt=='My Current Observation: observation\nWhat should I do next? Return only the JSON object.'
    actor.guidance='REPAIR';actor.act('next')
    assert p.prompt.startswith('My Memories: observation\nReasoning: Actual reasoning\nAction: inspect token\nREPAIR\n')
    assert not actor.guidance and not hasattr(actor,'notebook')


def test_same_judge_call_when_no_eligible_history_and_no_updater_change():
    class Provider:
        model='model';step=1
        def request(self,messages,**kwargs):
            self.messages=messages
            return {'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
    p=Provider();ledger=OutcomeLedger();judge=EvidenceJudge(p,ledger,True)
    judge('[SENTRY DETECTOR]\noriginal');assert p.messages[1]['content']=='[SENTRY DETECTOR]\noriginal'
    ledger.add(0,'take token','I took token.');judge.query='token';judge.before=1
    judge('[SENTRY DETECTOR]\noriginal');assert 'Additional historical' in p.messages[1]['content']
    judge('[SENTRY PLAYBOOK UPDATER]\noriginal');assert p.messages[1]['content']=='[SENTRY PLAYBOOK UPDATER]\noriginal'
