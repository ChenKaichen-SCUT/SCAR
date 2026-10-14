"""No-network native replay and isolated feasibility probes; no Agent changes."""
import contextlib
import argparse
import io
import math
import re
import tempfile
from collections import Counter
from .common import *
from scar_stage26.replay import Saved
from scar_stage25.integration import make_agent
from scar_stage27.verify import ledger

def main(archive_only=False):
    offline();integrity=check_freeze();assert read(RESULTS/'completion.json')['complete']
    from scar.environment import restore,state_digest,isolated_copy
    from scar.io import digest
    from agents.agc.state import extract
    from agents.agc.agent import DecisionUnavailable
    from scar.providers.deepseek import estimate_cost
    from scar_stage22.provider import prices_at
    receipts=[];allq=[];probes=[];verified=0;contexts=0
    for ident,s in selected().items():
        cp=CHECKPOINTS/ident;meta=read(RESULTS/'checkpoints'/ident/'meta.json')
        for variant in ['OriginalRecovery','OracleGoalStack']:
            out=(ROOT/f'results/stage28/runs/{ident}/OracleRecovery') if variant=='OriginalRecovery' else RESULTS/'runs'/ident/variant;summary=read(out/'summary.json')
            rr=rows(out/'trajectory.jsonl.gz')
            source=out
            qq=[q for q in rows(source/'requests.jsonl.gz') if q['step']>=meta['start']]
            intervention_records=[]
            class Replay(Saved):
                def generate(self,user_prompt,system_prompt=None,**kw):
                    base=[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)]
                    injected=self.step==meta['start']
                    if self.step==meta['start'] and self.ordinal==0:assert base==meta['original_first_messages']
                    actual=user_prompt+(meta['baseline_suffix'] if variant=='OriginalRecovery' else meta['suffix']) if injected else user_prompt
                    if variant=='OracleGoalStack':
                        intervention_records.append(dict(logical_id=f'{self.step:03d}:{self.ordinal+1:03d}',step=self.step,ordinal=self.ordinal+1,
                            injected=injected,base_messages_hash=digest(base),actual_messages_hash=digest([base[0],dict(role='user',content=actual)])))
                    return super().generate(actual,system_prompt,**kw)
            p=Replay(qq)
            with tempfile.TemporaryDirectory(prefix='scar30-verify-') as tmp:
                with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('remnant',42,p,Path(tmp)/'memory');agent.load_memory(cp)
                env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp,agent)
                assert state_digest(env)==s['post_state_hash']
                def probe(index):
                    before=state_digest(env)
                    with isolated_copy(env) as clone:
                        with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:s['candidate_action']});clone.update_scores(reward)
                        accepted=not extract(obs[AGENT_ID])['failed'] and not re.search(r'^Failed to\b',extract(obs[AGENT_ID])['feedback'],re.I) and not info.get('step_invalid_action',{}).get(AGENT_ID,False)
                        probes.append(dict(id=ident,variant=variant,continuation_step=index,absolute_step=env.steps,
                            pre_state_hash=before,action=s['candidate_action'],accepted=accepted,feedback=obs[AGENT_ID],reward=vars(reward[AGENT_ID]),
                            done=bool(done),info=info,post_probe_state_hash=state_digest(clone),model_calls=0))
                    assert state_digest(env)==before
                probe(0)
                for i,r in enumerate(rr,1):
                    p.begin_step(r['step']);assert env.obs[AGENT_ID]==r['observation'] and state_digest(env)==r['state_hash_before']
                    assert agent.short_term_memory==r['memory_before']
                    with contextlib.redirect_stdout(io.StringIO()):action,tin,tout,response=agent.act(r['observation'])
                    assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
                    with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                    assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward']
                    assert info==r['info'] and bool(done)==r['done'];agent.observe_transition(r['observation'],action,r['feedback'])
                    assert digest(agent.control.to_dict())==digest(r['control_after']);agent.control.events.clear();verified+=1
                    if i in {5,20,len(rr)}:probe(i)
                if variant=='OracleGoalStack' and summary['status']=='agent_decision_exhausted':
                    stop=read(out/'decision_exhausted.json');p.begin_step(stop['step'])
                    try:
                        with contextlib.redirect_stdout(io.StringIO()):agent.act(env.obs[AGENT_ID])
                    except DecisionUnavailable:pass
                    else:raise AssertionError('Terminal invalid decision did not reproduce')
                    assert digest(agent.decision)==digest(stop['decision']) and env.obs[AGENT_ID]==stop['observation']
                assert env.scores[AGENT_ID]==summary['scores']
                if variant=='OracleGoalStack':
                    agent.save_memory(Path(tmp)/'final')
                    for name in ['memory.json','agc_v2.json']:assert read(Path(tmp)/'final'/name)==read(out/'final_memory'/name)
                    assert intervention_records==rows(out/'interventions.jsonl.gz')
                    if not archive_only:
                        runtime=RUNTIME/'runs'/ident;assert not (runtime/'pending_request.json').exists()
                        ll=ledger(runtime/'budget.sqlite');assert {q['request_id'] for q in qq}=={x[0] for x in ll}
                        assert math.isclose(sum(x[1] for x in ll),summary['cost_usd'],abs_tol=1e-12)
                    assert len(p.calls)==sum(q['status']=='ok' for q in qq);allq.extend(qq)
            contexts+=len(p.calls);receipts.append(dict(id=ident,variant=variant,passed=True,native_actions=len(rr),model_contexts=len(p.calls)))
            print(json.dumps(receipts[-1]),flush=True)
    for q in allq:
        if q['status']=='ok':
            assert q['unit_prices']==prices_at(q['raw_response'].get('created') or q['start'])
            assert math.isclose(estimate_cost(q['usage'],q['unit_prices']),q['cost_usd'],abs_tol=1e-12)
        else:assert q['status']=='http_rejected' and q['charged_or_reserved_usd']==0
    assert len({q['request_id'] for q in allq})==len(allq)
    cost=sum(q.get('cost_usd',0) for q in allq)
    if not archive_only:
        ll=ledger(RUNTIME/'budget.sqlite');assert {q['request_id'] for q in allq}=={x[0] for x in ll}
        assert math.isclose(sum(x[1] for x in ll),cost,abs_tol=1e-12)
    gzwrite(RESULTS/'native_feasibility_probes.jsonl.gz',probes)
    write(RESULTS/'verification.json',dict(passed=True,exact_native_actions=verified,exact_model_contexts=contexts,receipts=receipts,
        isolated_probe_actions=len(probes),freeze_integrity=integrity,new_verification_model_calls=0))
    write(RESULTS/'cost_reconciliation.json',dict(passed=True,new_requests=len(allq),cost_usd=cost,
        input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in allq),output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in allq),
        statuses=dict(Counter(q['status'] for q in allq)),unknown_billing=0,unsettled_reservations=0 if not archive_only else None,
        private_sqlite_ledger_verified=not archive_only,
        provider_invoice_available=False,per_response_usage_and_saved_unit_prices_verified=True))
    print(json.dumps(dict(passed=True,requests=len(allq),cost_usd=cost,native_actions=verified,contexts=contexts)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive-only',action='store_true');main(p.parse_args().archive_only)
