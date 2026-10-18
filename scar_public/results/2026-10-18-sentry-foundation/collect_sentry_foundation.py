"""Retain all frozen pilot outcomes; no best-arm or favorable-world selection."""
import collections,gzip,hashlib,json,re,tarfile
from pathlib import Path
root=Path('/root/scar_sentry_foundation_20261018');out=root/'summary';out.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text())
manifest=read(root/'frozen/source_manifest.json')
for name,sha in manifest.items():
    if name!='parent_revision':assert hashlib.sha256((root/'frozen'/name).read_bytes()).hexdigest()==sha,name
summary=dict(qualification='Frozen evidence-access pilot, NOT the full persistent-blocker mechanism; one new draw per familiar game, not statistically stable improvement',
    source_manifest_sha256=hashlib.sha256((root/'frozen/source_manifest.json').read_bytes()).hexdigest(),
    frozen_files=len(manifest)-1,rows=[],coupling=[],probes={})
usages=[];files=[]
for game in ('remnant','mark','metropolis'):
    block=root/'evaluation'/game;traces={}
    for arm in ('base','sentry','evidence'):
        b=block/arm;r=read(b/'result.json');usages.append(r['usage'])
        traces[arm]=[read(p) for p in sorted((b/'trace').glob('*.json'))]
        events=[json.loads(s) for s in (b/'sentry_events.jsonl').read_text().splitlines()] if arm!='base' else []
        types=collections.Counter(e['type'] for e in events);escapes=[e for e in events if e['type']=='escape_result']
        retrieval=[json.loads(s) for s in (b/'retrieval.jsonl').read_text().splitlines()] if arm!='base' else []
        row=dict(game=game,arm=arm,**r,event_types=dict(types),
            verified_recoveries=sum(e['resolved'] for e in escapes),verification_count=len(escapes),
            augmented_judgments=sum(bool(e['selected_cycles']) for e in retrieval),
            total_extra_chars=sum(e['extra_chars'] for e in retrieval),
            score_curve={str(n):next((t['scores']['quest'] for t in traces[arm] if t['step']==n),r['scores']['quest']) for n in (50,100,150,200,250,300)})
        # Paid-cache ownership is a race between arms, so use logical usage for
        # method cost comparisons and summed paid usage for the actual batch.
        logical={k:r['usage'][k] for k in ('successful_responses','prompt_tokens','completion_tokens','cache_hit_tokens','peak_usd_estimate')}
        logical['shared_responses']=0
        reuse=b/'api/shared_reuse.jsonl'
        if reuse.exists():
            for item in map(json.loads,reuse.read_text().splitlines()):
                usage=read(Path(item['source']))['usage']
                logical['shared_responses']+=1;logical['successful_responses']+=1
                for k in ('prompt_tokens','completion_tokens'):logical[k]+=usage.get(k,0)
                logical['cache_hit_tokens']+=usage.get('prompt_cache_hit_tokens',0)
                hit=usage.get('prompt_cache_hit_tokens',0)
                logical['peak_usd_estimate']+=(hit*.006+max(0,usage.get('prompt_tokens',0)-hit)*.30+usage.get('completion_tokens',0)*1.20)/1e6
        row['logical_usage']=logical
        row['elapsed_seconds']=(b/'result.json').stat().st_mtime-(b/'manifest.json').stat().st_mtime
        summary['rows'].append(row)
        dest=out/game/arm;dest.mkdir(parents=True,exist_ok=True)
        for name in ('result.json','manifest.json','sentry_events.jsonl','retrieval.jsonl'):
            if (b/name).exists():(dest/name).write_bytes((b/name).read_bytes())
    for left,right in (('base','sentry'),('sentry','evidence'),('base','evidence')):
        matched=0;first=None
        for a,b in zip(traces[left],traces[right]):
            assert a['before_digest']==b['before_digest'] and a['observation']==b['observation'],(game,left,right,a['step'])
            if a['action']!=b['action']:first=a['step'];break
            assert a['after_digest']==b['after_digest'] and a['next_observation']==b['next_observation']
            matched+=1
        summary['coupling'].append(dict(game=game,left=left,right=right,matched_prefix_actions=matched,first_action_divergence=first))
for world in ('mark_r1','metropolis_r1'):
    p=read(root/'probes'/world/'result.json');usages.append(p['usage'])
    summary['probes'][world]=dict(count=len(p['rows']),
        intervention_retained=sum(r['evidence']['intervention_needed'] for r in p['rows']),
        original_label_counts=dict(collections.Counter(l for r in p['rows'] for l in r['original']['retrieval_labels'])),
        new_label_counts=dict(collections.Counter(l for r in p['rows'] for l in r['evidence']['retrieval_labels'])),
        qualification=p['qualification'])
    (out/(world+'_probe.json')).write_bytes((root/'probes'/world/'result.json').read_bytes())
summary['usage']={k:sum(u[k] for u in usages) for k in ('requests','successful_responses','peak_usd_estimate','unknown_charge_attempts','prompt_tokens','completion_tokens','summed_request_seconds')}
summary['replay_checks']=sum(r['replays'] for r in summary['rows'])
summary['common_prefix_checks']=sum(r['matched_prefix_actions'] for r in summary['coupling'])
summary['tests']=dict(unit_tests_passed=8,upstream_actor_equal_cycles=3,qualification='Three scripted no-API well-formed prompt/memory/action comparisons; not performance trials')
# Post-hoc explanatory case, not a selected evaluation subset or success metric.
events=[json.loads(s) for s in (root/'evaluation/metropolis/sentry/sentry_events.jsonl').read_text().splitlines()]
case=dict(qualification='Post-hoc illustration from original Sentry; not a causal ablation or prevalence estimate',cycles=[])
latest=None;chosen=None
for e in events:
    if e['type']=='agent_step':
        latest=e['step_id']
        if 226<=latest<=236:case['cycles'].append(e['step'])
    if e['type']=='rescue_injected' and latest==226:chosen=e['event_id'];case['intervention']=e
    if e['type']=='escape_result' and e['event_id']==chosen:case['verification']=e
assert len(case['cycles'])==11 and not case['verification']['resolved']
(out/'case_metro_capacity.json').write_text(json.dumps(case,ensure_ascii=False,indent=2))
(out/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(out/'source_manifest.json').write_bytes((root/'frozen/source_manifest.json').read_bytes())
for top in ('frozen','evaluation','probes'):
    for p in (root/top).rglob('*'):
        if not p.is_file():continue
        relative=p.relative_to(root)
        if any(x in relative.parts for x in ('environment','replay','initial_environment','__pycache__')):continue
        if p.suffix not in ('.py','.txt','.json','.jsonl','.gz','.log'):continue
        files.append((p,relative.as_posix()))
for p in root.glob('*.log'):files.append((p,p.name))
for name in ('sentry_history_probe_amended.py','launch_sentry_foundation.py','restart_sentry_probes.py','check_sentry_actor.py','collect_sentry_foundation.py'):
    files.append((Path('/root')/name,'evaluators/'+name))
for p in out.rglob('*'):
    if p.is_file():files.append((p,'summary/'+p.relative_to(out).as_posix()))
secrets=re.findall(r'sk-[A-Za-z0-9_-]+',Path('/root/scar_research_20261015/private/deepseek.key').read_text())
for p,name in files:
    data=gzip.decompress(p.read_bytes()) if p.name.endswith('.json.gz') else p.read_bytes()
    assert all(s.encode() not in data for s in secrets),'Secret scan failed'
archive=root/'public_evidence.tgz'
with tarfile.open(archive,'w:gz') as tar:
    for p,name in files:tar.add(p,arcname=name)
receipt=dict(files=len(files),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),api_key_scan='passed',private_snapshots='excluded')
(out/'public_evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
with tarfile.open(root/'summary.tgz','w:gz') as tar:tar.add(out,arcname='summary')
print(json.dumps(dict(rows=[{k:r[k] for k in ('game','arm','steps','scores','verified_recoveries','verification_count')} for r in summary['rows']],usage=summary['usage'],receipt=receipt)))
