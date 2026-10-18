"""Retain all frozen iterations, paid calls, cached controls and negative cases."""
import collections,gzip,hashlib,json,re,tarfile
from pathlib import Path
roots={'e1':Path('/root/scar_effect_20261018'),'e2':Path('/root/scar_effect_v2_20261018'),'e3':Path('/root/scar_effect_v3_20261018'),'e4':Path('/root/scar_effect_v4_20261018')}
read=lambda p:json.loads(p.read_text());out=roots['e4']/'summary';out.mkdir(exist_ok=True)
prior={r['name']:r for r in read(Path('/root/scar_plan_v2_20261018/summary/analysis.json'))['rows'] if r['version']=='p2'}
summary=dict(freeze={},probes=[],rows=[],qualification='Selected development states and previously used worlds; cached repeats are not independent. e4 is final code; all previous losses retained.')
usages=[];files=[];cases={}
for version,root in roots.items():
    manifest=read(root/'frozen/source_manifest.json')
    for name,sha in manifest.items():
        if name!='parent_revision':assert hashlib.sha256((root/'frozen'/name).read_bytes()).hexdigest()==sha,name
    summary['freeze'][version]=dict(files=len(manifest)-1,unchanged=True,source_sha256=hashlib.sha256((root/'frozen/source_manifest.json').read_bytes()).hexdigest())
    (out/(version+'_source_manifest.json')).write_bytes((root/'frozen/source_manifest.json').read_bytes())
    for job in read(root/'probe_jobs.json'):
        name=job['name'];p=read(root/'probes'/name/'result.json')
        row=dict(version=version,name=name,world=p['world'],prefix_replays=p['prefix_replays'],evaluator_binding=p['evaluator_binding'],budget_intervention=p['budget_intervention'],target=p['target'],
            branch_replays=sum(v['steps'] for v in p['results'].values()),
            arms={k:{f:v[f] for f in ('fulfilled','steps','score_delta','failures','overrides','proposal_calls_after','usage')} for k,v in p['results'].items()})
        summary['probes'].append(row);usages.extend(v['usage'] for v in p['results'].values())
        (out/(version+'_'+name+'.json')).write_bytes((root/'probes'/name/'result.json').read_bytes())
    if (root/'jobs.json').exists():
        for job in read(root/'jobs.json'):
            name=job['name'];b=root/'evaluation'/name;r=read(b/'result.json');old=prior[name]
            events=read(b/'events.json');outcomes=read(b/'outcomes.json')
            traces=[read(p) for p in sorted((b/'trace').glob('*.json'))]
            revisions=[e for e in events if 'proposal' in e and e.get('previous_repair')]
            rejections=collections.Counter(reason if isinstance(reason,str) else reason['reason'] for e in events for rej in e.get('initial_rejections',[])+e.get('program_rejections',[]) for reason in rej['reasons'])
            row=dict(version=version,name=name,checked=old['checked'],compact=old['compact'],sentry=old['sentry'],h2=old['h2'],objective=old['objective'],plan_p2=old['plan'],effect=r['scores']['quest'],**r,
                event_reasons=dict(collections.Counter(str(e.get('reason')) for e in events)),rejections=dict(rejections),
                compiled_stages=dict(collections.Counter(e['contract']['stage'] for e in events if e.get('reason')=='COMPILED_REQUIREMENT_PLAN')),
                revision_queries=len(revisions),root_fulfillment_records=[dict(step=o['step'],need=o['next_frontier']['need']) for o in outcomes if o.get('requirement_resolved')],
                quest_milestones={str(q):next((t['step'] for t in traces if t['scores']['quest']>=q),None) for q in (5,6,7,10,11,13,16,17)})
            if version in ('e3','e4'):
                prev='e2' if version=='e3' else 'e3';earlier=roots[prev]/'evaluation'/name;count=0
                for t in traces:
                    p=earlier/'trace'/f"{t['step']:04d}.json"
                    if p.exists() and all(t[k]==read(p)[k] for k in ('action','before_digest','after_digest')):count+=1
                row['same_transition_as_'+prev]=count
            summary['rows'].append(row);usages.append(r['usage'])
            chosen=set(range(48,59)) if name.startswith('mark') else {t['step']+offset for t in traces if t['response']['continuation']['changed'] for offset in (-1,0,1)}
            cases[version+'_'+name]=[{k:t[k] for k in ('step','action','observation','next_observation','scores','before_digest','after_digest')} |
                dict(decision={k:t['response']['continuation'][k] for k in ('original','executed','changed','reason','contract','frontier','plan_cancelled') if k in t['response']['continuation']}) for t in traces if t['step'] in chosen]
            if name=='mark_r1':cases[version+'_salvage']=[{k:t[k] for k in ('step','action','next_observation','scores','before_digest','after_digest')} for t in traces if 'disassembl' in t['action']]
            dest=out/version/name;dest.mkdir(parents=True,exist_ok=True)
            for f in ('manifest.json','result.json','events.json','outcomes.json','counterfactuals.json'):(dest/f).write_bytes((b/f).read_bytes())
    for top in ('frozen','probes','evaluation','audit'):
        for p in (root/top).rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:continue
            relative=p.relative_to(root)
            if any(x in relative.parts for x in ('environment','replay','counterfactual','private_replay')):continue
            if p.suffix not in ('.py','.json','.jsonl','.txt','.gz','.log'):continue
            files.append((p,version+'/'+relative.as_posix()))
    for p in root.glob('*.log'):files.append((p,version+'/'+p.name))
    if (root/'full_game_gate.json').exists():files.append((root/'full_game_gate.json',version+'/full_game_gate.json'))
audit=read(roots['e3']/'audit/result.json');usages.extend(audit['usage']);(out/'compiler_audit.json').write_bytes((roots['e3']/'audit/result.json').read_bytes())
summary['audit_prefix_replays']=audit['prefix_replays']
summary['total_usage']={k:sum(u[k] for u in usages) for k in ('requests','successful_responses','peak_usd_estimate','unknown_charge_attempts','prompt_tokens','completion_tokens','summed_request_seconds')}
summary['full_game_replays']=sum(r['replays'] for r in summary['rows']);summary['full_game_prefix_checks']=sum(r['prefix_checks'] for r in summary['rows'])
summary['probe_prefix_replays']=sum(p['prefix_replays'] for p in summary['probes']);summary['probe_branch_replays']=sum(p['branch_replays'] for p in summary['probes'])
summary['final_comparisons']={base:{key:sum(fn(r['effect'],r[base]) for r in summary['rows'] if r['version']=='e4') for key,fn in [('wins',lambda a,b:a>b),('ties',lambda a,b:a==b),('losses',lambda a,b:a<b)]} for base in ('checked','compact','sentry','h2','objective','plan_p2')}
opportunity={}
for version in ('e3','e4'):
    b=roots[version]/'evaluation/metropolis_7537/trace'
    start=read(b/'0206.json');rows=[read(b/f'{i:04d}.json') for i in range(207,215)]
    opportunity[version]=dict(initial_digest=rows[0]['before_digest'],initial_score=start['scores']['quest'],
        final_score=rows[-1]['scores']['quest'],score_delta=rows[-1]['scores']['quest']-start['scores']['quest'],
        rows=[{k:t[k] for k in ('step','action','observation','next_observation','scores','before_digest','after_digest')} for t in rows])
assert opportunity['e3']['initial_digest']==opportunity['e4']['initial_digest']
summary['opportunity_branch']=dict(qualification='Post-selected existing paired full-game suffix at decision 207; identical state/RNG and public prefix, no new rollout or independent replication',
    arms={k:{f:v[f] for f in ('initial_digest','initial_score','final_score','score_delta')} for k,v in opportunity.items()})
(out/'opportunity_branch.json').write_text(json.dumps(opportunity,ensure_ascii=False,indent=2))
(out/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(out/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
evaluators=['collect_effect.py','effect_probe.py','effect_probe_v2.py','effect_probe_v3.py','effect_probe_v4.py','launch_effect_probes.py','launch_effect_probes_v2.py','launch_effect_probes_v3.py','launch_effect_probes_v4.py','launch_effect_games.py','launch_effect_games_v3.py','launch_effect_games_v4.py','effect_audit.py','launch_effect_audit.py','queue_effect_replays.py','start_effect_queue.py','queue_effect_replays_v4.py','start_effect_queue_v4.py']
for name in evaluators:files.append((Path('/root')/name,'evaluators/'+name))
for p in out.rglob('*.json'):files.append((p,'summary/'+p.relative_to(out).as_posix()))
secrets=re.findall(r'sk-[A-Za-z0-9_-]+',Path('/root/scar_research_20261015/private/deepseek.key').read_text())
for p,name in files:
    data=gzip.decompress(p.read_bytes()) if p.name.endswith('.json.gz') else p.read_bytes()
    assert all(s.encode() not in data for s in secrets),'Secret scan failed'
archive=roots['e4']/'public_evidence.tgz'
with tarfile.open(archive,'w:gz') as tar:
    for p,name in files:tar.add(p,arcname=name)
receipt=dict(files=len(files),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),api_key_scan='passed',private_snapshots='excluded')
(out/'public_evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
with tarfile.open(roots['e4']/'summary.tgz','w:gz') as tar:tar.add(out,arcname='summary')
print(json.dumps(dict(rows=[{k:r[k] for k in ('version','name','effect','plan_p2','objective','overrides','proposal_calls')} for r in summary['rows']],usage=summary['total_usage'],receipt=receipt)))
