"""Collect both frozen development policies, including negative diagnostics."""
import collections,gzip,hashlib,json,re,tarfile
from pathlib import Path

roots={'p1':Path('/root/scar_plan_20261018'),'p2':Path('/root/scar_plan_v2_20261018')}
read=lambda p:json.loads(p.read_text())
out=roots['p2']/'summary';out.mkdir(exist_ok=True)
prior={r['name']:r for r in read(Path('/root/scar_objective_v3_20261018/summary/analysis.json'))['rows'] if r['version']=='o3'}
summary=dict(rows=[],freeze={},probes=[],qualification='Reused development worlds; one run/freeze, no independent replication or significance claim. Frozen baselines not rerun. p2 remains opt-in; p1 retained, not selected by best score.')
files=[];cases={};usages=[]
for version,root in roots.items():
    manifest=read(root/'frozen/source_manifest.json')
    for name,sha in manifest.items():
        if name!='parent_revision':assert hashlib.sha256((root/'frozen'/name).read_bytes()).hexdigest()==sha,name
    summary['freeze'][version]=dict(files=len(manifest)-1,unchanged=True,source_sha256=hashlib.sha256((root/'frozen/source_manifest.json').read_bytes()).hexdigest())
    (out/(version+'_source_manifest.json')).write_bytes((root/'frozen/source_manifest.json').read_bytes())
    for job in read(root/'jobs.json'):
        name=job['name'];block=root/'evaluation'/name;r=read(block/'result.json');old=prior[name]
        events=read(block/'events.json');outcomes=read(block/'outcomes.json')
        traces=[read(p) for p in sorted((block/'trace').glob('*.json'))]
        compiled=[e for e in events if e.get('reason')=='COMPILED_REQUIREMENT_PLAN']
        revisions=[e for e in events if e.get('packet',{}).get('frontier')]
        rejections=collections.Counter()
        for e in events:
            for reject in e.get('initial_rejections',[])+e.get('program_rejections',[]):
                for reason in reject['reasons']:rejections[reason if isinstance(reason,str) else reason['reason']]+=1
        hits=[json.loads(x) for x in (block/'api/historical_reuse.jsonl').read_text().splitlines()]
        row=dict(version=version,name=name,checked=old['checked'],compact=old['compact'],sentry=old['sentry'],h2=old['h2'],objective=old['objective'],plan=r['scores']['quest'],**r,
            compiled_decisions=len(compiled),compiled_stages=dict(collections.Counter(e['contract']['stage'] for e in compiled)),
            revision_queries=len(revisions),revision_overrides=sum(e['changed'] for e in revisions),
            root_requirements_fulfilled=sum(o['requirement_resolved'] is True for o in outcomes),
            root_fulfillment_records=[dict(step=o['step'],stage=o['contract']['stage'],need=o['next_frontier']['need']) for o in outcomes if o['requirement_resolved'] is True],
            milestone_true_root_false=sum(o['execution_outcome'] is True and o['requirement_resolved'] is False for o in outcomes),
            next_frontiers=dict(collections.Counter(o.get('next_frontier',{}).get('kind',o.get('next_frontier',{}).get('status','none')) for o in outcomes)),
            event_reasons=dict(collections.Counter(str(e.get('reason')) for e in events)),rejections=dict(rejections),
            historical_hits=len(hits),cache_sources=dict(collections.Counter(h.get('source','unspecified') for h in hits)),
            quest_milestones={str(q):next((t['step'] for t in traces if t['scores']['quest']>=q),None) for q in (5,6,10,11,13,16,17)})
        summary['rows'].append(row);usages.append(r['usage'])
        for low,high,label in ((48,65,'early_material_or_access'),(113,135,'access_revision')):
            if (label=='early_material_or_access' and name.startswith('mark')) or (label=='access_revision' and name=='metropolis_r1'):
                cases[version+'_'+name+'_'+label]=[t for t in traces if low<=t['step']<=high]
        if name=='metropolis_7537':cases[version+'_'+name+'_access_cycle']=[t for t in traces if 197<=t['step']<=216]
        dest=out/version/name;dest.mkdir(parents=True,exist_ok=True)
        for f in ('events.json','outcomes.json','manifest.json','result.json','counterfactuals.json'):(dest/f).write_bytes((block/f).read_bytes())
    for name in ('failed_source','positive_source'):
        p=read(root/'probes'/name/'result.json')
        dest=out/(version+'_'+name+'.json');dest.write_bytes((root/'probes'/name/'result.json').read_bytes())
        summary['probes'].append(dict(version=version,name=name,prefix_replays=p['prefix_replays'],
            branch_replays=sum(v['steps'] for v in p['results'].values()),evaluator_binding=p['evaluator_binding'],
            budget_intervention=p['budget_intervention'],legacy_proposal_calls=p['legacy_proposal_calls'],
            arms={k:{f:v[f] for f in ('fulfilled','steps','score_delta','proposal_calls_after','usage')} for k,v in p['results'].items()}))
        usages.extend(v['usage'] for v in p['results'].values())
    for top in ('frozen','evaluation','probes','audit'):
        for path in (root/top).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:continue
            relative=path.relative_to(root)
            if any(x in relative.parts for x in ('environment','replay','counterfactual','private_replay')):continue
            if path.suffix not in ('.py','.json','.jsonl','.txt','.gz','.log'):continue
            files.append((path,version+'/'+relative.as_posix()))
    for path in root.glob('*.log'):files.append((path,version+'/'+path.name))
audit=read(roots['p2']/'audit/result.json')
(out/'proposal_audit.json').write_bytes((roots['p2']/'audit/result.json').read_bytes())
summary['proposal_audit']={k:audit[k] for k in ('qualification','prefix_replays','p2_accepts_supplied_proposal','compiled_action','usage','interpretation')}
usages.append(audit['usage'])
summary['total_usage']={k:sum(u[k] for u in usages) for k in ('requests','successful_responses','peak_usd_estimate','unknown_charge_attempts','prompt_tokens','completion_tokens','summed_request_seconds')}
summary['full_game_replays']=sum(r['replays'] for r in summary['rows'])
summary['full_game_prefix_checks']=sum(r['prefix_checks'] for r in summary['rows'])
summary['probe_prefix_replays']=sum(p['prefix_replays'] for p in summary['probes'])
summary['probe_branch_replays']=sum(p['branch_replays'] for p in summary['probes'])
for version in roots:
    summary[version+'_comparisons']={baseline:{label:sum(compare(r['plan'],r[baseline]) for r in summary['rows'] if r['version']==version) for label,compare in [('wins',lambda x,y:x>y),('ties',lambda x,y:x==y),('losses',lambda x,y:x<y)]} for baseline in ('checked','compact','sentry','h2','objective')}
(out/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(out/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
evaluators=['collect_plan.py','plan_probe.py','plan_probe_v2.py','launch_plan.py','launch_plan_v2.py','launch_plan_probes.py','launch_plan_probes_v2.py','plan_proposal_audit.py','launch_plan_audit.py']
for name in evaluators:files.append((Path('/root')/name,'evaluators/'+name))
for path in out.rglob('*.json'):files.append((path,'summary/'+path.relative_to(out).as_posix()))
secrets=re.findall(r'sk-[A-Za-z0-9_-]+',Path('/root/scar_research_20261015/private/deepseek.key').read_text())
for path,name in files:
    data=gzip.decompress(path.read_bytes()) if path.name.endswith('.json.gz') else path.read_bytes()
    assert all(s.encode() not in data for s in secrets),'Secret scan failed'
archive=roots['p2']/'public_evidence.tgz'
with tarfile.open(archive,'w:gz') as tar:
    for path,name in files:tar.add(path,arcname=name)
receipt=dict(files=len(files),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),api_key_scan='passed',private_snapshots='excluded')
(out/'public_evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
with tarfile.open(roots['p2']/'summary.tgz','w:gz') as tar:tar.add(out,arcname='summary')
print(json.dumps(dict(rows=[{k:r[k] for k in ('version','name','plan','objective','checked','overrides','proposal_calls','revision_queries','root_requirements_fulfilled')} for r in summary['rows']],usage=summary['total_usage'],receipt=receipt)))
