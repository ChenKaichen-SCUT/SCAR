"""Offline native replay, exact prompt reconstruction and per-response accounting."""
import contextlib
import copy
import gzip
import io
import json
import math
import sqlite3
import tempfile
from collections import Counter
from .common import *
from .fixtures import make_messages,compile_state,provenance_check

def ledger(path):
    with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:return db.execute('select id,charged,status from requests').fetchall()

def main():
    offline();integrity=check_freeze();assert read(RESULTS/'completion.json')['complete']
    from scar.environment import restore,state_digest
    from scar.io import digest
    from scar.providers.deepseek import estimate_cost
    from scar_stage22.provider import prices_at
    allq=[];verified=0;contexts=0;receipts=[]
    for s in samples():
        for condition in ['understanding','A','B'] if s['action_test_eligible'] else ['understanding']:
            out=RESULTS/'probes'/s['id']/condition;runtime=RUNTIME/'requests'/s['id']/condition
            result=read(out/'result.json');qq=rows(out/'requests.jsonl.gz');allq.extend(qq)
            assert not (runtime/'pending_request.json').exists()
            ll=ledger(runtime/'budget.sqlite');assert {q['request_id'] for q in qq}=={x[0] for x in ll}
            assert math.isclose(sum(x[1] for x in ll),result['cost_usd'],abs_tol=1e-12)
            successful=[q for q in qq if q['status']=='ok'];probe_verified=0
            if condition=='understanding':
                assert len(successful)==1 and successful[0]['messages']==make_messages(s,condition);contexts+=1
                assert successful[0]['raw_response']['choices'][0]['message']['content']==result['response']
            else:
                cp=RESULTS/'checkpoints'/s['id'];prefix=json.loads(gzip.decompress((cp/'public_prefix.json.gz').read_bytes()))
                original=copy.deepcopy(s['original_messages']);chain=result['chain'];assert len(successful)==len(chain)
                with tempfile.TemporaryDirectory(prefix='scar27-verify-') as tmp:
                    env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp)
                    assert state_digest(env)==s['post_state_hash']
                    for c,q in zip(chain,successful):
                        state=compile_state(prefix);provenance_check(state,prefix)
                        messages=make_messages(s,condition,original,state)
                        assert q['messages']==messages and digest(messages)==c['messages_hash'];contexts+=1
                        assert q['raw_response']['choices'][0]['message']['content']==c['response']
                        assert c['observation']==env.obs[AGENT_ID] and c['state_hash_before']==state_digest(env)
                        if not c['syntax_valid']:continue
                        with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:c['action']});env.update_scores(reward)
                        assert state_digest(env)==c['state_hash'] and obs[AGENT_ID]==c['feedback'] and vars(reward[AGENT_ID])==c['reward']
                        assert info==c['info'] and bool(done)==c['done'];verified+=1;probe_verified+=1
                        prefix.append(dict(step=env.steps,action=c['action'],observation=c['observation'],feedback=c['feedback']))
                        original[-1]['content']+='\n\nOffline replay continuation:\nPrevious model JSON: '+c['response']+'\nActual environment observation:\n'+c['feedback']['text']+'\nWhat should I do next? Return only the JSON object.'
            receipts.append(dict(id=s['id'],condition=condition,native_actions=probe_verified,model_contexts=len(successful),passed=True))
    for q in allq:
        if q['status']=='ok':
            assert q['unit_prices']==prices_at(q['raw_response'].get('created') or q['start'])
            assert math.isclose(estimate_cost(q['usage'],q['unit_prices']),q['cost_usd'],abs_tol=1e-12)
        else:assert q['status']=='http_rejected' and q['charged_or_reserved_usd']==0
    ll=ledger(RUNTIME/'budget.sqlite');assert {q['request_id'] for q in allq}=={x[0] for x in ll}
    assert len({q['request_id'] for q in allq})==len(allq)
    cost=sum(q.get('cost_usd',0) for q in allq);assert math.isclose(sum(x[1] for x in ll),cost,abs_tol=1e-12)
    write(RESULTS/'verification.json',dict(passed=True,exact_native_actions=verified,exact_model_contexts=contexts,
        diagnostic_jobs=len(receipts),receipts=receipts,freeze_integrity=integrity,new_verification_model_calls=0))
    write(RESULTS/'cost_reconciliation.json',dict(passed=True,new_requests=len(allq),cost_usd=cost,
        input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in allq),output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in allq),
        statuses=dict(Counter(q['status'] for q in allq)),unknown_billing=0,unsettled_reservations=0,
        provider_invoice_available=False,per_response_usage_and_saved_unit_prices_verified=True))
    print(json.dumps(dict(passed=True,requests=len(allq),cost_usd=cost,native_actions=verified,contexts=contexts)),flush=True)

if __name__=='__main__':main()
