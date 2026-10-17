"""Audit compressed cores on already captured queries; no new timing claim."""
import argparse,json
from pathlib import Path
from time import perf_counter
import z3
from scar_public.study_reachable_labels import load
from scar_public.sparse_policy import SparseEncoding,compress_rule,replay_rule
from scar_public.finite_planner import State
from itertools import combinations


def main():
    p=argparse.ArgumentParser();p.add_argument('cache',type=Path);p.add_argument('queries',type=Path)
    p.add_argument('output',type=Path);a=p.parse_args();source=json.loads(a.queries.read_text())
    task,_=load(a.cache,source['config']);rows=[]
    for row in source['rows']:
        belief=frozenset((w['name'],State((w['bits'],w['allowed']),tuple(w['resources']))) for w in row['query'])
        start=perf_counter();rule,stats=compress_rule(task,belief,row['rule'],start+5.)
        seconds=perf_counter()-start;assert replay_rule(task,rule)
        # Exact optimistic-retirement pair test, distinct from strong-plan
        # feasibility. A failed strong pair can still pass optimistic coverage.
        states=dict(belief);enc=SparseEncoding(task,row['horizon']);pairs=[]
        for first,second in combinations(sorted(row['core']['members']),2):
            assumptions=[]
            for name in (first,second):
                f=enc.add_candidate(name,states[name],task.dynamic)
                assumptions += [f['use']]+list(f['links'].values())
            answer=enc.check(assumptions,perf_counter()+3.)
            pairs.append(dict(names=[first,second],answer=str(answer)))
        rows.append(dict(index=row['index'],before_candidates=len(row['core']['members']),
            after_candidates=len(rule['certificate']['members']),seconds=seconds,
            stats=stats,rule=rule,rule_replayed=True,optimistic_pairs=pairs))
    result=dict(rows=rows,compressed=sum(r['stats']['candidate_reduced'] for r in rows),
        queries=len(rows),api_calls=0,
        interpretation='Offline diagnostic, excluded from server timing. A negative strong-plan pair '
        'does not imply a negative optimistic-retirement pair. No global minimum claim.')
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps(dict(queries=len(rows),
        compressed=result['compressed'],seconds=sum(r['seconds'] for r in rows),
        pair_unsat=[r['index'] for r in rows if any(p['answer']=='unsat' for p in r['optimistic_pairs'])])))


if __name__=='__main__':main()
