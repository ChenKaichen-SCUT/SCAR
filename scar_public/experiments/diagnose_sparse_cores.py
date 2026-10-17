"""Explain the old Ring certificate without relabelling it as a joint gain."""
import argparse,json,platform
from pathlib import Path
from time import perf_counter
from math import inf
from scar_public.study_reachable_labels import configurations,load
from scar_public.sparse_policy import SparseEncoding
from scar_public.factored_progress import FactoredProgress
from scar_public.progress_carrier import causal_pattern
from scar_public.information_reference import independent_oracle
from scar_public.budgeted_planner import InferenceStop


def main():
    p=argparse.ArgumentParser();p.add_argument('cache',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    config=next(c for c in configurations() if c['id']=='lug_ring_4_a16s1')
    task,origin=load(a.cache,config);start=perf_counter();deadline=start+15.
    def check():
        if perf_counter()>deadline:raise InferenceStop()
    encoding=SparseEncoding(task,10,check)
    prune,answer=encoding.run(task.belief,deadline);finished=perf_counter()
    assert prune
    sufficient=answer['certificate'];minimal=encoding.minimize_certificate(deadline)
    minimized=perf_counter()
    subset=frozenset(w for w in task.belief if w[0] in minimal['members'])
    pattern=set().union(*(set(v) for v in minimal['links'].values())) | encoding.goals
    rows=[]
    for label,projection in (('old_causal_12',causal_pattern(task)),('core_link_union',tuple(sorted(pattern)))):
        c=FactoredProgress(task,projection);c.deadline=deadline;k=c.carrier(subset);now=perf_counter()
        rows.append(dict(projection=label,atoms=[task.atom_names[i] for i in projection],
            scalar=c.value(k,10),lineage=c.value(k,10,True),seconds=perf_counter()-now))
    oracle=independent_oracle(task)
    exact10=oracle(subset,10);exact11=oracle(subset,11)
    result=dict(config=config,origin=origin,python=platform.python_version(),platform=platform.platform(),
        seconds=finished-start,minimization_seconds=minimized-finished,
        sufficient_core=sufficient,minimal_core=minimal,
        core_atoms={n:[task.atom_names[i] for i in ids] for n,ids in minimal['links'].items()},
        rule=encoding.rule(minimal),statistics=encoding.stats,comparisons=rows,
        independent_oracle=dict(h10=str(exact10),h11=exact11),
        interpretation='The old 320/266 capacity gap is not intrinsically a large candidate conflict. '
            'This diagnostic permits progress-link refinement, and separately checks whether a stronger count absorbs it. '
            'Deletion minimality is only for this bounded encoding, not global minimum cardinality.')
    assert exact10==inf and exact11==11
    a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(seconds=result['seconds'],minimal_members=minimal['members'],
        minimal_links={n:len(v) for n,v in minimal['links'].items()},comparisons=rows,oracle=result['independent_oracle'])))


if __name__=='__main__':main()
