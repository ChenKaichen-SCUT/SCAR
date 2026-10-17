"""Measure the actual public-prefix review INCLUDING audit serialization."""
import argparse,json,platform,statistics
from pathlib import Path
from time import perf_counter
from scar_public.method_repair import MethodMemory,MethodController

def main():
    p=argparse.ArgumentParser();p.add_argument('old',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    run=a.old/'runtime/attributes_structured/evidence_repair_v11/metropolis'
    m=MethodMemory();m.load(json.loads((run/'checkpoints/0093/agent.json').read_text()))
    row=json.loads((run/'trace/0094.json').read_text());proposal=json.loads(row['response'])
    m.model.observe(row['observation'],m.last_action);c=MethodController(m);c.context_scope='attributes'
    review=c.review_proposal({**proposal,'action':proposal['guarded_evidence_review']['action']},row['observation'])
    c.record_rejection(review,93);times=[]
    for _ in range(101):
        start=perf_counter();result=c.assess_switch(proposal);serialized=json.dumps(result)
        times.append((perf_counter()-start)*1000)
    measured=times[1:]
    out=dict(scope='Microbenchmark on one selected real public history, not a game-speedup claim',
        platform=platform.platform(),first_ms=times[0],repetitions=100,median_ms=statistics.median(measured),
        p95_ms=sorted(measured)[94],max_ms=max(measured),serialized_audit_bytes=len(serialized.encode()),
        includes=['task binding','source evidence scan','recipe dependency','all quantity effects',
                  'option preservation','joint material schedule','JSON audit serialization'],
        excludes=['history reconstruction','LLM latency','navigation/acquisition search','engine actions'],api_requests=0)
    a.out.write_text(json.dumps(out,indent=2));print(json.dumps(out))

if __name__=='__main__':main()
