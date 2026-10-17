"""Exact small-model cost audit; reports all configurations, including unknowns."""
import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path
from time import perf_counter

from scar_public.test_resource_competition import problem
from scar_public.resource_competition import ResourceGap,compile_resources,select_experiment

def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args()
    rows=[]
    for need,held,bag,capacity in product((500,1000,1500),(0,1000,2000),(0,1000),(1000,2000)):
        if held>capacity:continue
        params=dict(needs=need,held=held,bag=bag,capacity=capacity,modes=('exact','ceil_batch'),
                    access=('hand','hand_bag'),quantities=(1,2))
        row=dict(parameters=params);t=perf_counter()
        try:
            c=compile_resources(problem(**params),horizon=4,max_states=12000)
            reports=[]
            for gate in (False,True):
                start=perf_counter();r,_,_=select_experiment(c,prefix_depth=2,max_prefixes=40,
                    expansion_budget=600,mode='preserve_opportunity',require_profile_nondegradation=gate)
                reports.append(dict(gate=gate,seconds=perf_counter()-start,report=r))
            row.update(states=c.states,reports=reports)
        except ResourceGap as error:row['gap']=str(error)
        row['seconds']=perf_counter()-t;rows.append(row)
    candidates=[candidate for row in rows for run in row.get('reports',[]) if run['gate']
                for candidate in run['report']['candidates']]
    changed=[r for r in rows if 'reports' in r and any(
        r['reports'][0]['report'].get(k)!=r['reports'][1]['report'].get(k) for k in ('status','prefix','first_action'))]
    result=dict(scope='Constructed mechanism matrix, not independent benchmark or game performance',
        configurations=len(rows),gaps=sum('gap' in r for r in rows),
        decisions=dict(Counter(c['decision'] for c in candidates)),changed_selection=len(changed),rows=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))

if __name__=='__main__':main()
