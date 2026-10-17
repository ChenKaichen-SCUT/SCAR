"""Read-only public-trace applicability audit before paid LLM experiments."""
import argparse,json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from scar_public.obligations import ExecutionModel
from scar_public.resource_trial import from_public
from scar_public.resource_competition import ResourceGap


def audit(directory):
    model=ExecutionModel();previous=None;rows=[];reasons=Counter();eligible=[];targets=0
    trace_paths=sorted((directory/'trace').glob('*.json'));hashes=[]
    for path in trace_paths:
        raw=path.read_bytes();r=json.loads(raw);hashes.append(sha256(raw).hexdigest())
        model.observe(r['observation'],previous)
        parsed=json.loads(r['response']);target=parsed.get('resource_target','')
        if r['action'].startswith('craft '):target=r['action'].split()[-1]
        row=dict(step=r['step'],action=r['action'],target=target,
            source=parsed.get('decision_source','llm'),main=r['scores'].get('quest',0))
        if target and target in model.recipes:
            targets+=1
            try:
                problem=from_public(model,r['observation'],target)
                row.update(groundable=True,location=problem.start_location)
                eligible.append(dict(step=r['step'],target=target,location=problem.start_location))
            except ResourceGap as error:
                row.update(groundable=False,reason=str(error));reasons[str(error)]+=1
        rows.append(row);previous=r['action']
    return dict(game=directory.name,trace_steps=len(rows),targets=targets,eligible=eligible,
        failures=dict(reasons),rows=rows,trace_hash_chain=sha256(''.join(hashes).encode()).hexdigest(),
        final=json.loads((directory/'current.json').read_text()),
        manifest=json.loads((directory/'manifest.json').read_text()))


def main():
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();result=dict(api_calls=0,hidden_state_read=False,games=[])
    for game in ('remnant','mark','metropolis'):
        row=audit(a.runtime/'round7/obligation_v6'/game);result['games'].append(row)
        print(json.dumps({k:row[k] for k in ('game','trace_steps','targets','eligible','failures')}),flush=True)
    result['baselines']=[dict(method=m,game=g,current=json.loads((a.runtime/'round1'/m/g/'current.json').read_text()),
        manifest=json.loads((a.runtime/'round1'/m/g/'manifest.json').read_text()))
        for m in ('stm','longcontext','reflact') for g in ('remnant','mark','metropolis')]
    a.output.write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
