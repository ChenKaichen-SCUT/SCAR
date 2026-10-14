"""Saved-response native replay and same-state candidate/final probes."""
import argparse,contextlib,copy,io,math,tempfile
from collections import Counter
from scar_stage26.replay import Saved
from scar_stage27.verify import ledger
from scar_stage22.provider import prices_at
from agents.agc.agent import DecisionUnavailable
from agents.saer.state import rejected
from scar.agents.scar.repair import valid_syntax
from scar.io import digest
from .common import *
from .integration import make_agent

def main(archive_only=False):
    offline();integrity=check_freeze();assert read(RESULTS/'online_completion.json')['complete']
    from scar.environment import restore,state_digest,isolated_copy
    from scar.providers.deepseek import estimate_cost
    probes=[];receipts=[];allq=[]
    for seed in SEEDS:
        out=RESULTS/'runs'/ident(seed);rr=rows(out/'trajectory.jsonl.gz');qq=rows(out/'requests.jsonl.gz');s=read(out/'summary.json');p=Saved(qq)
        with tempfile.TemporaryDirectory(prefix='scar32-verify-') as tmp:
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(seed,p,Path(tmp)/'memory')
            env=restore(gzip.decompress((initial(seed)/'physical.pkl.gz').read_bytes()),tmp,agent);agent.initialize_official(env.obs[AGENT_ID])
            def candidate_probes(n,decision,actual=None):
                before=state_digest(env)
                for i,rec in enumerate(decision.get('saer_records',[]),1):
                    if 'prediction' not in rec:continue
                    pair={}
                    for field,proposal in [('candidate',rec['candidate']),('final',rec.get('final_proposal'))]:
                        action=proposal.get('action','') if isinstance(proposal,dict) else ''
                        if not isinstance(action,str) or not valid_syntax(action.strip(),agent.available_actions):pair[field]=None;continue
                        with isolated_copy(env) as clone:
                            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:action.strip()});clone.update_scores(reward)
                            pair[field]=dict(action=action.strip(),feedback=obs[AGENT_ID],reward=vars(reward[AGENT_ID]),done=bool(done),info=info,
                                accepted=not rejected(obs[AGENT_ID]) and not info.get('step_invalid_action',{}).get(AGENT_ID,False),state_hash=state_digest(clone))
                        assert state_digest(env)==before
                    final_applied=bool(actual and i==len(decision['saer_records']) and pair['final'] and pair['final']['action']==actual['action'])
                    if final_applied:assert pair['final']['feedback']==actual['feedback'] and pair['final']['state_hash']==actual['state_hash']
                    probes.append(dict(seed=seed,step=n,reflection_index=i,source_state_hash=before,pair=pair,warning=rec['warning'],prediction=rec['prediction'],
                        final_applied=final_applied,terminal=actual is None,new_model_calls=0))
            for r in rr:
                n=r['step'];p.begin_step(n);assert state_digest(env)==r['state_hash_before'] and env.obs[AGENT_ID]==r['observation']
                assert agent.short_term_memory==r['memory_before'] and agent.task_state.to_dict()==r['task_before']
                with contextlib.redirect_stdout(io.StringIO()):action,ti,to,response=agent.act(r['observation'])
                assert action==r['action'] and digest(agent.decision)==digest(r['decision']);assert ti==r['input_tokens'] and to==r['output_tokens']
                candidate_probes(n,agent.decision,r)
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback'] and vars(reward[AGENT_ID])==r['reward'];assert info==r['info']
                agent.observe_transition(r['observation'],action,obs[AGENT_ID]);assert agent.control.to_dict()==r['control_after'] and agent.task_state.to_dict()==r['task_after'];agent.control.events.clear()
            if s['status']=='agent_decision_exhausted':
                t=read(out/'decision_exhausted.json');p.begin_step(t['step'])
                try:
                    with contextlib.redirect_stdout(io.StringIO()):agent.act(env.obs[AGENT_ID])
                except DecisionUnavailable:pass
                else:raise AssertionError('Native terminal decision did not reproduce')
                assert agent.decision==t['decision'];candidate_probes(t['step'],agent.decision)
            agent.save_memory(Path(tmp)/'final')
            for name in agent.memory_paths:assert read(Path(tmp)/'final'/name)==read(out/'final_memory'/name)
            assert len(p.calls)==sum(q['status']=='ok' for q in qq);assert env.scores[AGENT_ID]==s['scores']
        allq.extend(qq);receipts.append(dict(seed=seed,actions=len(rr),contexts=len(p.calls),passed=True));print(json.dumps(receipts[-1]),flush=True)
    for q in allq:
        if q['status']=='ok':
            assert q['unit_prices']==prices_at(q['raw_response'].get('created') or q['start']);assert math.isclose(q['cost_usd'],estimate_cost(q['usage'],q['unit_prices']),abs_tol=1e-12)
        else:assert q['status']=='http_rejected' and q['charged_or_reserved_usd']==0
    assert len({q['request_id'] for q in allq})==len(allq);cost=sum(q.get('cost_usd',0) for q in allq)
    if not archive_only:
        assert not list(RUNTIME.rglob('pending_request.json'));ll=ledger(RUNTIME/'budget.sqlite')
        assert {x[0] for x in ll}=={q['request_id'] for q in allq};assert math.isclose(sum(x[1] for x in ll),cost,abs_tol=1e-12)
        for path in list((RUNTIME/'runs').glob('*/budget.sqlite')):
            ep=ledger(path);own=[q for q in allq if q['request_id'] in {x[0] for x in ep}]
            assert len(own)==len(ep) and math.isclose(sum(q['cost_usd'] for q in own),sum(x[1] for x in ep),abs_tol=1e-12)
    gzwrite(RESULTS/'online_native_probes.jsonl.gz',probes)
    write(RESULTS/'verification.json',dict(passed=True,receipts=receipts,exact_native_actions=sum(x['actions'] for x in receipts),exact_model_contexts=sum(x['contexts'] for x in receipts),
        isolated_probe_actions=sum(sum(p is not None for p in x['pair'].values()) for x in probes),new_verification_model_calls=0,freeze_integrity=integrity,
        baseline_reuse_verification='Existing seed42 AGC-v2 baseline already verified in Stage31; unchanged files covered by this freeze.'))
    write(RESULTS/'cost_reconciliation.json',dict(passed=True,new_requests=len(allq),cost_usd=cost,input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in allq),
        output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in allq),statuses=dict(Counter(q['status'] for q in allq)),private_ledgers_verified=not archive_only,
        unknown_billing=0,provider_invoice_available=False,analysis_model_calls=0))
    print(json.dumps(dict(passed=True,new_requests=len(allq),cost_usd=cost)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive-only',action='store_true');main(p.parse_args().archive_only)
