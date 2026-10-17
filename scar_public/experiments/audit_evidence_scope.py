"""Chronological, read-only guard diagnostic on actual public trajectories.

Wider scopes here are diagnostic alternatives, NOT deployed policies. All
predictions precede feedback assimilation. No new game or model calls.
"""
import argparse
from collections import Counter
from dataclasses import replace
from itertools import product
import json
from pathlib import Path

from scar_public.obligations import ExecutionModel
from scar_public.evidence_repair import scoped_problem,semantic_context
from scar_public.resource_evidence import EvidenceBank
from scar_public.resource_competition import ResourceDomain,ResourceGap
from scar_public.resource_trial import fresh,public_outcome

def context(text,scope):
    c=semantic_context(text)
    if scope=='attributes':c.pop('clock_cell')
    return c

def scan(rows,scope):
    model=ExecutionModel();bank=EvidenceBank();previous=None;records=[]
    for row in rows:
        text=row['observation'];action=row['action'];model.observe(text,previous);previous=action
        if not action.startswith('craft '):continue
        record=dict(step=row['step'],action=action)
        try:
            p=scoped_problem(model,text,action.split()[-1])
            p=replace(p,source={**p.source,'semantic_context':context(text,scope)})
            domain=ResourceDomain(p)
            if action not in domain.actions:raise ResourceGap('unsupported batch command')
            review=bank.review_action(p,action)
            after=row['next_observation'];status=public_outcome(after,action)
            actual=fresh(after)
            record.update(grounded=True,review=review,actual_status=status,
                physically_unchanged=fresh(text)==actual)
            if context(after,scope)!=context(text,scope):raise ResourceGap('context changed on acquisition')
            if actual['equipped']!=p.source['equipment'] or 'I was attacked' in after:raise ResourceGap('external state change')
            if set(actual['holding'])-set(p.items):raise ResourceGap('unmodeled held item')
            if not status:raise ResourceGap('outcome unknown')
            vector=lambda values:tuple(values.get(n,0) for n in p.items)
            obs=(status,actual['location'],vector(actual['holding']),vector(actual['ground']),(status=='success',),None)
            r=p.recipes[0]
            compatible={pair for pair in product(r.quantity_modes,r.access_modes)
                        if domain.transition({r.output:pair},domain.start,action)[1]==obs}
            key,entry=bank.entry(p);before=set(map(tuple,entry['allowed']));survivors=before&compatible
            if not survivors:raise ResourceGap('all retained models mismatch')
            entry['allowed']=sorted(survivors);entry['observations']+=1
            record.update(eliminated=len(before-survivors),remaining=len(survivors))
        except ResourceGap as error:
            record['gap']=str(error)
            if record.get('grounded'):bank.invalidate(p,str(error))
        records.append(record)
    reviewed=[r for r in records if r.get('review')]
    return dict(scope=scope,craft_proposals=len(records),grounded=sum(r.get('grounded',False) for r in records),
        exclusions=sum(bool(r.get('eliminated')) for r in records),would_reject=len(reviewed),
        contradicted_rejections=sum(r.get('actual_status')!='failure' or not r.get('physically_unchanged') for r in reviewed),
        gaps=dict(Counter(r['gap'] for r in records if 'gap' in r)),records=records)

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    runs=[]
    for directory in sorted((a.root/'runtime').glob('*/*/*/trace')):
        rows=[json.loads(p.read_text()) for p in sorted(directory.glob('*.json'))]
        runs.append(dict(arm=directory.parts[-4],game=directory.parts[-2],
            scopes=[scan(rows,scope) for scope in ('clock','attributes')]))
    result=dict(scope='Post-run chronological diagnostic; broader guard NOT deployed or a performance result',runs=runs)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    for run in runs:
        print(json.dumps(dict(arm=run['arm'],game=run['game'],scopes=[{k:r[k] for k in
            ('scope','craft_proposals','grounded','exclusions','would_reject','contradicted_rejections','gaps')} for r in run['scopes']])))

if __name__=='__main__':main()
