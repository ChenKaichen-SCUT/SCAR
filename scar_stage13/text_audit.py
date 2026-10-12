"""Posthoc public-text novelty sensitivity; never changes frozen policy/metric.

Stage12 ResourceTable parses '(made of ...)' but not native acquisition feedback
'(2 x, 0.5 y)'. This independent diagnostic treats both as public recipe disclosure.
It is not an online patch or a new claim of an optimal parser.
"""
import collections
import gzip
import json
from pathlib import Path
import re
from scar.io import atomic_json
from scar_stage13.analyze import load,OUT,OLD


def extract(text):
    out={}
    for name, body in re.findall(r'([\w-]+) \(([^)]+)\)',text):
        if body.startswith('made of '):
            values=[x.strip() for x in body[8:].split(',')]
            if values and all(re.fullmatch(r'[\w-]+',x) for x in values):out[name]=values
        else:
            tokens=[re.fullmatch(r'(\d+(?:\.\d+)?) ([\w-]+)',x.strip()) for x in body.split(',')]
            if tokens and all(tokens):out[name]=[m.group(2) for m in tokens]
    return out


def main():
    states=load(OLD/'states.json');inputs={r['state_id']:r['public'] for r in load(OUT/'public_inputs.json')}
    cases={c['id']:c for c in load('results/stage11/cases.json')}
    branches={r['state_id']:r['branches'] for r in map(json.loads,gzip.open(OLD/'native_branches.jsonl.gz','rt'))}
    metrics=load(OUT/'state_metrics.json');by={(r['state_id'],r['method']):r for r in metrics};rows=[]
    for s in states:
        sid=s['state_id'];case=cases[s['case_id']];pub=inputs[sid];known={};sources=[]
        # Only publicly presented strings and frozen ResourceTable enter this
        # parser. Native keys below only score necessity after disclosure.
        observations=[]
        for h in case['history']:observations.extend([h['before'],h['after']])
        for h in pub['history']:observations.extend([h['before'],h['after']])
        observations.append(s['observation'])
        for obs in observations:
            for n,deps in extract(obs['text']).items():
                if n not in known:sources.append({'recipe':n,'ingredients':deps,'observed_step':obs.get('step'),
                    'public_text':obs['text']})
                known[n]=deps
        for n,r in pub['controller']['table']['recipes'].items():
            if r.get('ingredients'):known.setdefault(n,r['ingredients'])
        keys={case['object_names'][k] for k in case['recipe_graph']}
        outcomes={}
        for cid,b in branches[sid].items():
            disclosed={}
            for tr in b['trace']:disclosed.update(extract(tr['after']['text']))
            new=sorted((set(disclosed)-set(known))&keys)
            outcomes[cid]={'new_native_necessary_public_text_recipes':new,'useful':bool(new),
                'stage12_parser_useful':b['useful'], 'new_vs_initial_public_text':True}
        selected={m:outcomes[by[sid,m]['candidate_id']] for m in ['C0','C1','C2','C3','L','J3']}
        rows.append({'state_id':sid,'family':by[sid,'C0']['family'],
            'initial_public_text_necessary_recipes':sorted(set(known)&keys),
            'initial_public_text_recipe_sources':sources,
            'all_branch_outcomes':outcomes,'selected':selected,
            'public_menu_has_opportunity':any(outcomes[c['id']]['useful'] for c in s['candidates'])})
    summary={m:{'useful':sum(r['selected'][m]['useful'] for r in rows),
        'gains_vs_C0':[r['state_id'] for r in rows if r['selected'][m]['useful'] and not r['selected']['C0']['useful']],
        'losses_vs_C0':[r['state_id'] for r in rows if r['selected']['C0']['useful'] and not r['selected'][m]['useful']]} for m in ['C0','C1','C2','C3','L','J3']}
    atomic_json(OUT/'public_text_novelty_audit.json',{'posthoc':True,'policy_unchanged':True,
        'stage12_primary_metric_unchanged':True,'parser':'both made-of and explicit quantified ingredient listings',
        'initial_history_public_strings_included':True,'public_menu_opportunity_states':sum(r['public_menu_has_opportunity'] for r in rows),
        'summary':summary,'rows':rows,'limitation':'disclosure of ingredient names, not proof of quantity feasibility, execution success or all possible textual relations'})
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
