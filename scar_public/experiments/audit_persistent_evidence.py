"""Zero-API matched-query audit; controlled models and chronological public data.

This is not a new game run. Historical observations are exogenous data from v8;
counterfactual v9 actions are never claimed to have produced those observations.
"""
import argparse
import json
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from scar_public.resource_agent import OPTIONS, problem_from_data
from scar_public.resource_competition import compile_resources, select_experiment
from scar_public.resource_evidence import EvidenceBank
from scar_public.resource_trial import TrialSession
from scar_public.test_resource_competition import problem


def plan(p, allowed=None, horizon=6, allowance=0):
    start=perf_counter()
    c=compile_resources(p,horizon=horizon,max_states=12000,allowed_profiles=allowed)
    built=perf_counter()
    r,w,pl=select_experiment(c,mode='preserve_opportunity',prefix_depth=2,
        max_prefixes=40,expansion_budget=600,max_extra_actions=allowance)
    end=perf_counter()
    summary=dict(status=r['status'],models=len(c.models),states=c.states,
        first_action=w['prefix'][0] if w and 'prefix' in w else w.get('action') if w else None,
        certified_cost=r.get('worst_total_actions'),compile_seconds=built-start,
        search_seconds=end-built,expansions=r.get('search_expansions',0))
    return summary,c,r,w,pl


def controlled():
    rows=[]
    for cap in (1000,2000):
        p=problem(needs=1000,held=0,bag=1000,capacity=cap,modes=('exact',),access=('hand','hand_bag'))
        bank=EvidenceBank(); _,meta=bank.query(p)
        baseline,c,report,w,planner=plan(p,horizon=4,allowance=1)
        assert w['prefix']==['craft 1 blade']
        # Synthetic public observation from the declared accessible-bag model.
        name=next(n for n,h in c.hypotheses.items() if h['blade']==('exact','hand_bag'))
        actual=next(m for m in c.models if m.name==name)
        _,obs=actual.step(c.domain.start,'craft 1 blade')
        survivors=sorted(n for n,_ in planner.branches(c.belief,'craft 1 blade')[obs])
        bank.observe(c,dict(status='ACTIVE',action='craft 1 blade',observed=obs,
            observation_sha256='synthetic-accessible-bag',surviving_models=survivors),meta['epoch'])
        later=replace(p,bag={'ore':2000})  # Same semantics, replenished material.
        allowed,reuse=bank.query(later)
        fresh,*_=plan(later,horizon=4)
        persistent,*_=plan(later,allowed,horizon=4)
        assert fresh['certified_cost']=='3' and persistent['certified_cost']=='2'
        assert fresh['first_action'].startswith('take out') and persistent['first_action']=='craft 1 blade'
        rows.append(dict(hand_capacity=cap,acquisition=baseline,query=reuse,fresh=fresh,persistent=persistent))
    return rows


def historical(source):
    rows=[]; audits={}
    for game in source['new_runs']:
        bank=EvidenceBank()
        for trial in sorted(game['selected_trials'],key=lambda t:t['step']):
            old=trial['selection']; p=problem_from_data(old['grounding'])
            allowed,metadata=bank.query(p)
            fresh,c,report,w,planner=plan(p)
            assert c.fingerprint==old['fingerprint'] and report['status']==old['status']
            reused=plan(p,allowed)[0] if allowed else dict(fresh)
            rows.append(dict(game=game['game'],step=trial['step'],target=p.target,
                evidence=metadata,fresh=fresh,persistent=reused,
                decision_changed=(fresh['status'],fresh['first_action'],fresh['certified_cost']) !=
                                 (reused['status'],reused['first_action'],reused['certified_cost'])))
            if w:
                s=TrialSession(c,report,w,planner)
                # No later observation enters a prior query. Replay only the
                # historical policy; filtered-policy results above stay offline.
                for action in game['actual_controller_actions']:
                    if action['controller']['fingerprint']!=c.fingerprint: continue
                    assert s.action()==action['action']
                    event=s.observe(action['next_observation'])
                    bank.observe(c,event,metadata['epoch'])
                    if s.status!='ACTIVE': break
        audits[game['game']]=bank.state
    return rows,audits


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('input',type=Path); parser.add_argument('output',type=Path)
    a=parser.parse_args()
    controls=controlled(); rows,audits=historical(json.loads(a.input.read_text(encoding='utf-8')))
    result=dict(protocol='Matched queries; chronological evidence; zero API; no new game-score claim',
        controlled=controls,historical=rows,ledgers=audits,
        summary=dict(historical_queries=len(rows),reused=sum(r['evidence']['reused'] for r in rows),
                     decisions_changed=sum(r['decision_changed'] for r in rows)))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result['summary']))
    for r in rows:
        print(r['game'],r['step'],r['evidence']['reused'],r['fresh']['models'],
              r['persistent']['models'],r['decision_changed'])


if __name__=='__main__': main()
