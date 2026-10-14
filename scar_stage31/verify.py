"""Exact no-network replay, same-state proposal probes and ledger reconciliation."""
import argparse
import contextlib
import copy
import io
import math
import tempfile
from collections import Counter
from agents.rec_v1.state import Tracker,failed,visible
from agents.agc.agent import DecisionUnavailable
from scar_stage26.replay import Saved
from scar_stage27.verify import ledger
from .common import *
from .integration import make_agent
from .metrics import source,goal

def main(archive_only=False):
    offline();integrity=check_freeze();assert read(RESULTS/'completion.json')['complete']
    from scar.environment import restore,state_digest,isolated_copy
    from scar.io import digest
    from scar.providers.deepseek import estimate_cost
    from scar_stage22.provider import prices_at
    allnew=[];receipts=[];probes=[]
    for seed,method in CASES:
        out=source(seed,method);s=read(out/'summary.json');rr=rows(out/'trajectory.jsonl.gz');qq=rows(out/'requests.jsonl.gz');p=Saved(qq)
        with tempfile.TemporaryDirectory(prefix='scar31-verify-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(seed,method,p,Path(tmp)/'memory')
            env=restore(gzip.decompress((initial(seed)/'physical.pkl.gz').read_bytes()),tmp,agent);agent.initialize_official(env.obs[AGENT_ID]);shadow=Tracker()
            def probe(step,action,kind,extra=None,retry_action=None):
                original=state_digest(env)
                with isolated_copy(env) as clone:
                    with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:action});clone.update_scores(reward)
                    probes.append(dict(case=case_id(seed,method),step=step,action=action,kind=kind,source_state_hash=original,
                        feedback=obs[AGENT_ID],reward=vars(reward[AGENT_ID]),done=bool(done),info=info,
                        accepted=not failed(obs[AGENT_ID]) and not info.get('step_invalid_action',{}).get(AGENT_ID,False),
                        visible=visible(obs[AGENT_ID]),craft_success='I successfully crafted ' in obs[AGENT_ID]['text'],
                        state_hash=state_digest(clone),evidence=extra,new_model_calls=0))
                    if retry_action:
                        second_before=state_digest(clone)
                        with contextlib.redirect_stdout(io.StringIO()):second,reward2,done2,info2=clone.step({AGENT_ID:retry_action});clone.update_scores(reward2)
                        probes[-1]['then_retry_last_rejected_action']=dict(action=retry_action,source_state_hash=second_before,
                            feedback=second[AGENT_ID],reward=vars(reward2[AGENT_ID]),done=bool(done2),info=info2,
                            accepted=not failed(second[AGENT_ID]) and not info2.get('step_invalid_action',{}).get(AGENT_ID,False),
                            visible=visible(second[AGENT_ID]),state_hash=state_digest(clone),new_model_calls=0)
                assert state_digest(env)==original
            for r in rr:
                n=r['step'];assert state_digest(env)==r['state_hash_before'] and env.obs[AGENT_ID]==r['observation']
                assert agent.short_term_memory==r['memory_before'];p.begin_step(n)
                if method=='REC':assert digest(agent.rec.to_dict())==digest(r['rec_before'])
                with contextlib.redirect_stdout(io.StringIO()):action,ti,to,response=agent.act(r['observation'])
                assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
                assert ti==r['input_tokens'] and to==r['output_tokens']
                for i,record in enumerate(agent.decision.get('rec_records',[]),1):
                    if record['check']['decision']=='RECONSIDER':probe(n,record['proposal']['action'].strip(),'blocked_proposal',dict(record=record,record_index=i,actual_action=action))
                shadow.ingest(r['observation']);assessment=shadow.assess(dict(action=action,goal_description=goal(r)));req=assessment['requirements'];test=None
                if any(x['kind'] in ['required_resource_custody_risk','facility_departure_risk'] for x in assessment['reasons']):
                    test=f"craft {req['amount']:g} {req['target']}";probe(n,test,'before_actual_risk',assessment)
                dark=visible(r['observation']) and not visible(r['feedback']) and 'too dark to see' in r['feedback']['text'].lower()
                if dark and action.startswith(('drop ','store ','unequip ')):probe(n,'wait','visibility_alternative',dict(actual_action=action))
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward']
                assert info==r['info'] and bool(done)==r['done'];agent.observe_transition(r['observation'],action,obs[AGENT_ID])
                assert digest(agent.control.to_dict())==digest(r['control_after']);agent.control.events.clear()
                if method=='REC':assert digest(agent.rec.to_dict())==digest(r['rec_after'])
                shadow.observe(r['observation'],action,r['feedback'],goal(r))
                if test:probe(n,test,'after_actual_risk',assessment)
            if s['status']=='agent_decision_exhausted':
                stop=read(out/'decision_exhausted.json');p.begin_step(stop['step']);assert env.obs[AGENT_ID]==stop['observation']
                try:
                    with contextlib.redirect_stdout(io.StringIO()):agent.act(env.obs[AGENT_ID])
                except DecisionUnavailable:pass
                else:raise AssertionError('Terminal decision did not reproduce')
                assert digest(agent.decision)==digest(stop['decision'])
                for i,record in enumerate(agent.decision.get('rec_records',[]),1):
                    if record['check']['decision']=='RECONSIDER':probe(stop['step'],record['proposal']['action'].strip(),'terminal_blocked_proposal',dict(record=record,record_index=i),
                        retry_action=rr[-1]['action'] if rr and failed(rr[-1]['feedback']) else None)
            assert env.scores[AGENT_ID]==s['scores'];assert len(p.calls)==sum(q['status']=='ok' for q in qq)
            agent.save_memory(Path(tmp)/'final')
            for name in agent.memory_paths:assert read(Path(tmp)/'final'/name)==read(out/'final_memory'/name),name
            newq=[] if seed==42 and method=='AGC-v2' else rows(out/'new_requests.jsonl.gz')
            assert len({q['request_id'] for q in qq})==len(qq)
            if newq and not archive_only:
                runtime=RUNTIME/'runs'/case_id(seed,method);assert not (runtime/'pending_request.json').exists();ll=ledger(runtime/'budget.sqlite')
                assert {q['request_id'] for q in newq}=={x[0] for x in ll}
                assert math.isclose(sum(x[1] for x in ll),sum(q['cost_usd'] for q in newq),abs_tol=1e-12)
            allnew.extend(newq)
        receipts.append(dict(case=case_id(seed,method),passed=True,actions=len(rr),exact_contexts=len(p.calls),new_requests=len(newq)))
        print(json.dumps(receipts[-1]),flush=True)
    for q in allnew:
        if q['status']=='ok':
            assert q['unit_prices']==prices_at(q['raw_response'].get('created') or q['start'])
            assert math.isclose(estimate_cost(q['usage'],q['unit_prices']),q['cost_usd'],abs_tol=1e-12)
        else:assert q['status']=='http_rejected' and q['charged_or_reserved_usd']==0
    cost=sum(q.get('cost_usd',0) for q in allnew);assert len({q['request_id'] for q in allnew})==len(allnew)
    if not archive_only:
        ll=ledger(RUNTIME/'budget.sqlite');assert {q['request_id'] for q in allnew}=={x[0] for x in ll};assert math.isclose(sum(x[1] for x in ll),cost,abs_tol=1e-12)
    gzwrite(RESULTS/'online_native_probes.jsonl.gz',probes)
    write(RESULTS/'verification.json',dict(passed=True,receipts=receipts,exact_native_actions=sum(x['actions'] for x in receipts),
        exact_model_contexts=sum(x['exact_contexts'] for x in receipts),isolated_native_probes=len(probes),
        isolated_probe_actions=len(probes)+sum('then_retry_last_rejected_action' in p for p in probes),freeze_integrity=integrity,new_verification_model_calls=0))
    write(RESULTS/'cost_reconciliation.json',dict(passed=True,new_requests=len(allnew),cost_usd=cost,
        input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in allnew),output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in allnew),
        statuses=dict(Counter(q['status'] for q in allnew)),unknown_billing=0,unsettled_reservations=0 if not archive_only else None,
        private_sqlite_ledger_verified=not archive_only,provider_invoice_available=False,per_response_usage_and_saved_unit_prices_verified=True))
    print(json.dumps(dict(passed=True,new_requests=len(allnew),cost_usd=cost,probes=len(probes))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive-only',action='store_true');main(p.parse_args().archive_only)
