"""Replayable root recurrence audit and deployed-selector check for Rover-4."""
import argparse,json
from pathlib import Path
from time import perf_counter
from scar_public.search_public_separations import load
from scar_public.certificate_refinement import projection_view
from scar_public.incremental_channels import IncrementalCoverage,IncrementalPlanner


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=json.loads(a.input.read_text())
    row=next(r for r in source['rows'] if r['config']['id']=='rovers_pfile4_a16s1')
    q=next(q for q in row['queries'] if q['status']=='SEPARATION' and q['projection']=='automatic')
    task,origin=load(a.cache,row['config']);ids={tuple(n):i for i,n in enumerate(task.atom_names)}
    extra=sum(1<<ids[tuple(n)] for n in q['added_atoms']);bound=IncrementalCoverage(projection_view(task,extra))
    depth=q['depth'];key=bound.canonical(bound.project(next(iter(task.belief))[1]),depth)
    mask=(1<<len(task.models))-1
    count=bound.capacity(key,depth);value=bound.relational_capacity(key,mask,depth)
    witness=bound.witness_value(key,mask,depth);audit=[]
    for action,goals,channels in bound.mask_channels[key]:
        immediate=mask&goals;remaining=mask&~goals;children=[]
        for eligible,nxt in channels:
            surviving=remaining&eligible
            child=bound.relational_capacity(nxt,surviving,depth-1)
            children.append(dict(eligible=eligible,surviving=surviving,capacity=child,successor=nxt))
        contribution=min(mask.bit_count(),immediate.bit_count()+sum(c['capacity'] for c in children))
        audit.append(dict(action=action,immediate=immediate,children=children,contribution=contribution))
    assert max(r['contribution'] for r in audit)==value==3 and count==4
    chosen=bound.scalar_witness[key,depth]
    scalar_action=bound.mask_channels[key][chosen][0]
    runs=[]
    for identifier in ('rovers_pfile2_original','rovers_pfile4_original','rovers_pfile4_a16s1'):
        entry=next(r for r in source['rows'] if r['config']['id']==identifier)
        t,_=load(a.cache,entry['config']);started=perf_counter();planner=IncrementalPlanner(t)
        answer=planner.solve(t.belief,16)
        assert answer.exact and answer.upper<float('inf')
        assert planner.verify(t.belief,16,answer.policy)==answer.upper
        runs.append(dict(id=identifier,value=answer.upper,seconds=perf_counter()-started,statistics=planner.statistics()))
    a.output.write_text(json.dumps(dict(config=row['config'],origin=origin,depth=depth,
        added_atoms=q['added_atoms'],scalar=count,identity=value,scalar_witness_under_identities=witness,
        scalar_witness_root_action=scalar_action,root_action_audit=audit,
        deployed_selector_runs=runs,scope='Post-discovery recurrence certificate plus three deployed dynamic-selector checks. '
        'H=16; not part of the 39-case 15s performance study.'),indent=2))
    print(json.dumps(dict(scalar=count,identity=value,witness=witness,root_actions=len(audit),
        deployed_runs=[dict(id=r['id'],value=r['value'],seconds=r['seconds']) for r in runs])))


if __name__=='__main__':main()
