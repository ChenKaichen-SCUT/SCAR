"""Post-hoc attribution of Cube rejection cores; never a timing/holdout run."""
import argparse, json, platform
from itertools import combinations
from math import inf
from pathlib import Path
from time import perf_counter
import z3
from scar_public.study_reachable_labels import configurations, load
from scar_public.sparse_policy import SparsePolicyPlanner, SparseEncoding, replay_rule
from scar_public.factored_progress import FactoredProgress
from scar_public.information_reference import independent_oracle
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


def main():
    p=argparse.ArgumentParser();p.add_argument('cache',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    config=next(c for c in configurations() if c['id']=='lug_cubecenter_3_a16s1')
    task,origin=load(a.cache,config);planner=SparsePolicyPlanner(task);captured=[]
    old=planner.target_coverage.decide
    def record(belief,budget,mode):
        rejected,e=old(belief,budget,mode)
        if rejected and e['reason']=='sparse_policy_prune':
            captured.append((belief,budget,e))
        return rejected,e
    planner.target_coverage.decide=record
    result=planner.solve(task.belief,config['horizon'])
    assert result.exact and planner.verify(task.belief,config['horizon'],result.policy)==result.upper
    rows=[]; oracle=independent_oracle(task)
    for index,(belief,h,evidence) in enumerate(captured):
        assert replay_rule(task,evidence['rule'])
        encoding=SparseEncoding(task,h)
        for name,state in belief:
            if name in evidence['certificate']['members']:
                encoding.add_candidate(name,state,evidence['certificate']['links'].get(name,()))
        labels=[z3.Bool(s) for s in evidence['certificate']['core_labels']]
        assert encoding.check(labels)==z3.unsat
        cert=encoding.minimize_certificate(deadline=perf_counter()+5.)
        rule=encoding.rule(cert);assert replay_rule(task,rule)
        subset=frozenset(w for w in belief if w[0] in cert['members'])
        # These small Cube contexts use the independent exhaustive oracle. This
        # check restores ALL facts; a SAT relaxed pair is not a feasible pair.
        single=[oracle(frozenset([w]),h) for w in subset]
        pairs=[oracle(frozenset(ws),h) for ws in combinations(subset,2)]
        pattern=tuple(sorted(set().union(*(set(ids) for ids in cert['links'].values())) | encoding.goals))
        comparisons=[]
        for label,worlds in (('minimal_core',subset),('full_query',belief)):
            carrier=FactoredProgress(task,pattern);carrier.deadline=perf_counter()+3.;started=perf_counter()
            key=carrier.carrier(worlds)
            row=dict(subset=label,candidates=sum(not task.goal.holds(s) for _,s in worlds),projection=[task.atom_names[p] for p in pattern])
            try:
                row['scalar']=carrier.value(key,h)
                row['lineage']=carrier.value(key,h,True)
                row['complete']=True
            except (InferenceStop,Unavailable):
                row['complete']=False
            row['seconds']=perf_counter()-started;comparisons.append(row)
        row=dict(index=index,horizon=h,live_candidates=sum(not task.goal.holds(s) for _,s in belief),
            original=evidence,core=cert,rule=rule,rule_replayed=True,
            query=[dict(name=n,bits=s.symbols[0],allowed=s.symbols[1],resources=s.resources) for n,s in sorted(belief)],
            singleton_values=[str(v) if v==inf else v for v in single],
            pair_values=[str(v) if v==inf else v for v in pairs],
            all_singletons_feasible=all(v<=h for v in single),
            all_pairs_feasible=bool(pairs) and all(v<=h for v in pairs),comparisons=comparisons)
        rows.append(row)
        a.output.write_text(json.dumps(dict(config=config,origin=origin,rows=rows,complete=False),indent=2))
        print(json.dumps(dict(index=index,h=h,members=cert['members'],single=row['all_singletons_feasible'],
            pairs=row['all_pairs_feasible'],comparisons=comparisons)),flush=True)
    a.output.write_text(json.dumps(dict(config=config,origin=origin,python=platform.python_version(),
        rows=rows,complete=True,plan_value=result.upper,plan_replayed=True,
        interpretation='Post-hoc diagnostics of reused development inputs, not independent experiments. '
        'Rule replay rebuilds the same encoding; singleton/pair attribution uses a separate unpruned oracle.'),indent=2))


if __name__=='__main__':main()
