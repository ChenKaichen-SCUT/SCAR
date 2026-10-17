"""Post-run source-quality and byte-identity audit; never selects by performance."""
import json
from pathlib import Path
from collections import defaultdict,Counter
from scar_public.label_scale_suite import source_text,configurations
from scar_public.contingent_benchmarks import sexpr

def audit(cache,out):
    prior=set()
    def walk(x):
        if isinstance(x,dict):
            hashes=x.get('content_sha256')
            if isinstance(hashes,list) and len(hashes)==2:prior.add(tuple(hashes))
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    for p in Path('scar_public/results').rglob('manifest.json'):
        if p.parent==out:continue
        try:walk(json.loads(p.read_text(encoding='utf-8')))
        except (ValueError,UnicodeError):pass
    entries=[];seen=defaultdict(list)
    for c in configurations()[::2]:
        d,p,o=source_text(cache,c);r=dict(id=c['id'],family=c['family'],syntax_error=o['syntax_error'])
        pair=(o['domain_sha256'],o['problem_sha256']);r['previous_identical_raw_pair']=pair in prior
        seen[pair].append(c['id'])
        if not o['syntax_error']:
            d,p=sexpr(d),sexpr(p)
            dn=next(x[1] for x in d if isinstance(x,list) and x[0]=='domain')
            pn=next(x[1] for x in p if isinstance(x,list) and x[0]==':domain')
            r.update(domain_name=dn,problem_domain=pn,domain_names_match=dn==pn)
        else:r['domain_names_match']=False
        entries.append(r)
    ids={r['id'].removesuffix('_original') for r in entries if r['domain_names_match']}
    rows=[json.loads(l) for l in (out/'runs.jsonl').read_text().splitlines()]
    cohorts={}
    for mode in sorted({r['mode'] for r in rows}):
        selected=[r for r in rows if r['mode']==mode and r['config']['id'].removesuffix('_original').removesuffix('_a16s1') in ids]
        supported=[r for r in selected if r['status']!='UNSUPPORTED_INPUT']
        solved=lambda r:r['status'] in ('PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H')
        cohorts[mode]=dict(configurations=len(selected),supported=len(supported),completed=sum(map(solved,selected)),
            statuses=dict(Counter(r['status'] for r in selected)),
            par2_supported=sum(r['total_seconds'] if solved(r) else 60 for r in supported)/len(supported))
    result=dict(entries=entries,prior_raw_pairs=len(prior),duplicates=[v for v in seen.values() if len(v)>1],
        coherent_domain_name_cohort=cohorts,
        scope='Post-run audit. Coherent-name cohort is NOT a full strict-PDDL conformance certification. '
        'The frozen frontend interpreted explicitly supplied domain/problem pairs and did not validate '
        'the problem domain reference. BT and Medical results require that declared interpretation. '
        'All rows retained; no outcome-based filtering. No identical raw pair in prior manifests is '
        'only a byte-level check, not a proof of semantic or statistical independence.')
    (out/'input_audit.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    import sys
    r=audit(Path(sys.argv[1]),Path(sys.argv[2]));print(json.dumps(r['coherent_domain_name_cohort'],indent=2))
