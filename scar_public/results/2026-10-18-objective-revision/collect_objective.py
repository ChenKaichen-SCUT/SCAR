import collections,gzip,hashlib,json,re,tarfile
from pathlib import Path
roots={'o1':Path('/root/scar_objective_20261018'),'o2':Path('/root/scar_objective_v2_20261018'),'o3':Path('/root/scar_objective_v3_20261018')}
read=lambda p:json.loads(p.read_text())
out=roots['o3']/'summary';out.mkdir(exist_ok=True)
prior={r['name']:r for r in read(Path('/root/scar_hypothesis_v2_20261018/summary/analysis.json'))['rows'] if r['version']=='h2'}
summary=dict(rows=[],freeze={},qualification='Existing development worlds, one run/freeze. No independent validation or significance claim. Frozen baselines not rerun. o3 is final code.')
files=[];cases={}
for version,root in roots.items():
    manifest=read(root/'frozen/source_manifest.json')
    for name,sha in manifest.items():
        if name!='parent_revision':assert hashlib.sha256((root/'frozen'/name).read_bytes()).hexdigest()==sha,name
    summary['freeze'][version]=dict(files=len(manifest)-1,unchanged=True,source_sha256=hashlib.sha256((root/'frozen/source_manifest.json').read_bytes()).hexdigest())
    (out/(version+'_source_manifest.json')).write_bytes((root/'frozen/source_manifest.json').read_bytes())
    for job in read(root/'jobs.json'):
        name=job['name'];block=root/'evaluation'/name;r=read(block/'result.json')
        events=read(block/'events.json');outcomes=read(block/'outcomes.json');old=prior[name]
        rejected=collections.Counter()
        for e in events:
            for reject in e.get('initial_rejections',[])+e.get('program_rejections',[]):
                for reason in reject['reasons']:rejected[reason if isinstance(reason,str) else reason['reason']]+=1
        selected=[e for e in events if e.get('reason')=='REQUIREMENT_BOUND_HYPOTHESIS']
        revisions=[e for e in events if e.get('packet',{}).get('revision_of') is not None]
        reuse=block/'api/historical_reuse.jsonl'
        hits=[json.loads(x) for x in reuse.read_text().splitlines()] if reuse.exists() else []
        row=dict(version=version,name=name,checked=old['checked'],compact=old['compact'],sentry=old['sentry'],h2=old['hypothesis'],
            objective=r['scores']['quest'],**r,selected_programs=len(selected),
            selected_modes=dict(collections.Counter(e['contract']['objective']['mode'] for e in selected)),
            revision_events=len(revisions),revision_selected=sum(e.get('reason')=='REQUIREMENT_BOUND_HYPOTHESIS' for e in revisions),
            revision_overrides=sum(e['changed'] for e in revisions),
            execution_true_requirement_false=sum(o['execution_outcome'] is True and o['outcome'] is False for o in outcomes),
            fulfilled_requirements=sum(o['requirement_resolved'] is True for o in outcomes),
            outcome_statuses=dict(collections.Counter(o['status'] for o in outcomes)),
            event_reasons=dict(collections.Counter(str(e.get('reason')) for e in events)),rejections=dict(rejected),
            historical_hits=len(hits),cache_sources=dict(collections.Counter(h.get('source','unspecified') for h in hits)))
        traces=[read(p) for p in sorted((block/'trace').glob('*.json'))]
        row['quest_milestones']={str(q):next((t['step'] for t in traces if t['scores']['quest']>=q),None) for q in (2,3,5,6,10,17)}
        summary['rows'].append(row)
        if version=='o3':
            dest=out/name;dest.mkdir(exist_ok=True)
            for f in ('events.json','outcomes.json','manifest.json','result.json','counterfactuals.json'):(dest/f).write_bytes((block/f).read_bytes())
        if version=='o3' and name=='mark_r0':cases['source_then_acquisition']=[t for t in traces if 58<=t['step']<=63]
        if version=='o1' and name=='metropolis_r1':cases['unsuccessful_native_revision']=[t for t in traces if 71<=t['step']<=76]
        if version=='o3' and name=='metropolis_r1':cases['reject_unrelated_endpoint']=[t for t in traces if t['step'] in (71,115)]
    for top in ('frozen','evaluation','audit','revision_probe'):
        for path in (root/top).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:continue
            relative=path.relative_to(root)
            if any(x in relative.parts for x in ('environment','replay','counterfactual','private_replay')):continue
            if path.suffix not in ('.py','.json','.jsonl','.txt','.gz','.log'):continue
            files.append((path,version+'/'+relative.as_posix()))
    for path in root.glob('*.log'):files.append((path,version+'/'+path.name))
audit=read(roots['o1']/'audit/audit.json');probe=read(roots['o3']/'revision_probe/result.json')
(out/'selected_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
(out/'selected_revision_probe.json').write_text(json.dumps(probe,ensure_ascii=False,indent=2))
summary['selected_diagnostics']=dict(compiler_audit_replays=audit['replayed_environment_transitions'],compiler_audit_new_requests=0,
    legacy_budget_preflight_prefix_replays=188,legacy_budget_preflight_new_requests=0,
    legacy_budget_preflight_result='No paid call: legacy prefix had already spent 12 proposal calls; assertion and log retained',
    probe_prefix_replays=probe['prefix_replays'],probe_new_transition_replays=probe['new_transition_replays'],
    probe_legacy_calls=probe['legacy_proposal_calls'],probe_budget_intervention=probe['budget_intervention'],probe_usage=probe['usage'])
usage=[r['usage'] for r in summary['rows']]+[probe['usage']]
summary['total_usage']={k:sum(u[k] for u in usage) for k in ('requests','successful_responses','peak_usd_estimate','unknown_charge_attempts','prompt_tokens','completion_tokens','summed_request_seconds')}
summary['full_game_replays']=sum(r['replays'] for r in summary['rows'])
summary['full_game_prefix_checks']=sum(r['prefix_checks'] for r in summary['rows'])
summary['final_vs_checked']={label:sum(compare(r['objective'],r['checked']) for r in summary['rows'] if r['version']=='o3') for label,compare in [('wins',lambda x,y:x>y),('ties',lambda x,y:x==y),('losses',lambda x,y:x<y)]}
summary['final_vs_h2']={label:sum(compare(r['objective'],r['h2']) for r in summary['rows'] if r['version']=='o3') for label,compare in [('wins',lambda x,y:x>y),('ties',lambda x,y:x==y),('losses',lambda x,y:x<y)]}
(out/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(out/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
evaluators=['/root/collect_objective.py','/root/objective_audit.py','/root/objective_revision_probe.py','/root/objective_revision_probe_v3.py',
    '/root/launch_objective.py','/root/launch_objective_v2.py','/root/launch_objective_v3.py']
for file in evaluators:files.append((Path(file),'evaluators/'+Path(file).name))
for path in out.rglob('*.json'):files.append((path,'summary/'+path.relative_to(out).as_posix()))
secrets=re.findall(r'sk-[A-Za-z0-9_-]+',Path('/root/scar_research_20261015/private/deepseek.key').read_text())
for path,name in files:
    data=gzip.decompress(path.read_bytes()) if path.name.endswith('.json.gz') else path.read_bytes()
    assert all(s.encode() not in data for s in secrets),'Secret scan failed'
archive=roots['o3']/'public_evidence.tgz'
with tarfile.open(archive,'w:gz') as tar:
    for path,name in files:tar.add(path,arcname=name)
receipt=dict(files=len(files),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),api_key_scan='passed',private_snapshots='excluded')
(out/'public_evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
with tarfile.open(roots['o3']/'summary.tgz','w:gz') as tar:tar.add(out,arcname='summary')
print(json.dumps(dict(rows=[{k:r[k] for k in ('version','name','objective','checked','h2','overrides','proposal_calls','revision_events')} for r in summary['rows']],usage=summary['total_usage'],receipt=receipt)))
