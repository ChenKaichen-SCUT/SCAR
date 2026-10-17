"""Discover recurring craft queries using public pre-action history only."""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import json
from pathlib import Path
import tarfile

from scar_public.obligations import ExecutionModel
from scar_public.resource_trial import from_public
from scar_public.resource_competition import ResourceGap
from scar_public.resource_evidence import evidence_context


def scan(rows, game, method):
    model=ExecutionModel(); previous=None; found=[]
    for index,row in enumerate(rows):
        model.observe(row['observation'],previous)
        action=row['action']; previous=action
        if not action.startswith('craft '): continue
        target=action.split()[-1]
        case=dict(game=game,method=method,step=row.get('step',index+1),target=target,action=action,
                  public_observation=row['observation'])
        try:
            p=from_public(model,row['observation'],target)
            key,guard=evidence_context(p)
            case.update(grounded=True,context=key,guard=guard,problem=asdict(p))
        except ResourceGap as e: case.update(grounded=False,reason=str(e))
        found.append(case)
    return found


def main():
    p=argparse.ArgumentParser();p.add_argument('--v8',type=Path,required=True)
    p.add_argument('--v6',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();all_rows=[]
    with tarfile.open(a.v8) as z:
        for game in ('mark','metropolis','remnant'):
            rows=[json.load(z.extractfile(m)) for m in z.getmembers() if '/'+game+'/trace/' in m.name]
            rows.sort(key=lambda r:r['step'])
            all_rows+=scan(rows,game,'v8')
            rows=json.loads((a.v6/(game+'.public.json')).read_text(encoding='utf-8'))
            all_rows+=scan(rows,game,'v6')
    groups=defaultdict(list)
    for r in all_rows:
        if r['grounded']:groups[(r['method'],r['game'],r['target'],r['context'])].append(r['step'])
    result=dict(scope='Public-prefix discovery; selected development traces, not independent evaluation',
        craft_queries=len(all_rows),grounded=sum(r['grounded'] for r in all_rows),
        repeated=[dict(method=k[0],game=k[1],target=k[2],context=k[3],steps=v)
                  for k,v in groups.items() if len(v)>1],queries=all_rows)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='queries'},indent=2))


if __name__=='__main__':main()
