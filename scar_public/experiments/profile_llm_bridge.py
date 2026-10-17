"""Offline replay of committed local problems; never calls LLM or environment.

Measurements are separated compilation/search costs, not in-run instrumented
timings. Save one measurement per fingerprint; subsequent calls reuse results.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter
from scar_public.resource_competition import Recipe,ResourceProblem,compile_resources,select_experiment
from scar_public.resource_agent import OPTIONS


def main():
    p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();results=json.loads(a.results.read_text())
    timings=json.loads(a.output.read_text()) if a.output.exists() else {}
    for game in results['new_runs']:
        for trial in game['selected_trials']:
            original=trial['selection'];fingerprint=original['fingerprint']
            if fingerprint in timings:continue
            d=dict(original['grounding'])
            d['recipes']=tuple(Recipe(r['output'],tuple(tuple(n) for n in r['needs']),tuple(r['stations']),
                tuple(r['quantity_modes']),tuple(r['access_modes']),tuple(r['quantities'])) for r in d['recipes'])
            for name in ('locations','items','assumptions'):d[name]=tuple(d[name])
            d['protected_totals']=tuple(tuple(t) for t in d['protected_totals'])
            start=perf_counter()
            compiled=compile_resources(ResourceProblem(**d),horizon=OPTIONS['horizon'],max_states=OPTIONS['max_states'])
            built=perf_counter()
            report,_,_=select_experiment(compiled,**{k:v for k,v in OPTIONS.items() if k not in ('horizon','max_states')})
            elapsed=perf_counter()
            replay=json.loads(json.dumps(dict(report,grounding=asdict(compiled.domain.problem))))
            assert compiled.fingerprint==fingerprint and original==replay
            timings[fingerprint]=dict(game=game['game'],step=trial['step'],target=d['target'],
                compilation_seconds=built-start,search_seconds=elapsed-built,status=report['status'],
                state_count=report['state_count'],search_expansions=report.get('search_expansions',0))
            a.output.write_text(json.dumps(timings,indent=2))
            print(json.dumps(timings[fingerprint]),flush=True)


if __name__=='__main__':main()
