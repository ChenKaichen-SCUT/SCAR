"""Collect all frozen outcomes, including negative and inconclusive arms."""
import collections,gzip,hashlib,json,re,tarfile
from pathlib import Path
root=Path('/root/scar_sentry_persistent_20261018_v2');failed=Path('/root/scar_sentry_persistent_20261018')
old=Path('/root/scar_sentry_foundation_20261018');out=root/'summary';out.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text())
manifest=read(root/'frozen/source_manifest.json')
for name,sha in manifest.items():
    if name!='parent_revision':assert hashlib.sha256((root/'frozen'/name).read_bytes()).hexdigest()==sha,name
assert not list((failed/'evaluation').rglob('attempts.jsonl')),'Startup failure unexpectedly made paid calls'
before=(failed/'frozen/scar_public/experiments/sentry_persistent_trial.py').read_text()
after=(root/'frozen/scar_public/experiments/sentry_persistent_trial.py').read_text()
assert before.replace("env.scores[AGENT_ID]['quest'];failures=0","env.scores.get(AGENT_ID,{}).get('quest',0);failures=0")==after
assert (failed/'frozen/scar_public/sentry_persistent.py').read_bytes()==(root/'frozen/scar_public/sentry_persistent.py').read_bytes()
summary=dict(qualification='Known development worlds, one trajectory per arm. Evidence for heuristics, not stable improvement or generalization.',
    source_manifest_sha256=hashlib.sha256((root/'frozen/source_manifest.json').read_bytes()).hexdigest(),
    frozen_files=len(manifest)-1,rows=[],baseline_rows=read(old/'summary/analysis.json')['rows'],coupling=[],action_audits={})
usages=[];case_records=[]
for game in ('remnant','mark','metropolis'):
    block=root/'evaluation'/game;traces={}
    for mode in ('advice','execute'):
        b=block/mode;r=read(b/'result.json');usages.append(r['usage']);traces[mode]=[read(p) for p in sorted((b/'trace').glob('*.json'))]
        events=[e for row in traces[mode] for e in row['persistent_events']];cards=[e for e in events if e['type']=='persistent_card']
        choices=[e for e in events if e['type']=='persistent_choice'];sentry=[e for row in traces[mode] for e in row['sentry_events']]
        escapes=[e for e in sentry if e['type']=='escape_result']
        logical={};paths={p.name:p for p in (b/'api').glob('*.response.json')}
        reuse=b/'api/shared_reuse.jsonl'
        if reuse.exists():
            for item in map(json.loads,reuse.read_text().splitlines()):
                path=Path(item['source']);paths[path.name]=path
        logical['unique_model_requests']=len(paths)
        for key in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens'):
            logical[key]=sum(read(path).get('usage',{}).get(key,0) for path in paths.values())
        row=dict(game=game,mode=mode,**r,logical_usage=logical,card_count=len(cards),
            structural_rejections=sum(len(e['structural_errors']) for e in cards),invalid_cards=sum(e['card'] is None for e in cards),
            status_counts=dict(collections.Counter(e['card']['status'] for e in cards if e['card'])),
            eligible_choices=sum(e['eligible'] for e in choices),changed_actions=sum(e['changed'] for e in choices),
            same_action_reasoning_replacements=sum(t['action']==t['proposed']['action'] and t['response']['reasoning']!=t['proposed']['reasoning'] for t in traces[mode]),
            verified_recoveries=sum(e['resolved'] for e in escapes),verifications=len(escapes),
            score_curve={str(n):next((t['scores']['quest'] for t in traces[mode] if t['step']==n),r['scores']['quest']) for n in (50,100,150,200,250,300)})
        summary['rows'].append(row)
        case_records.append(dict(game=game,mode=mode,cards=cards,changed_choices=[e for e in choices if e['changed']]))
    equal=0;first=None
    for x,y in zip(traces['advice'],traces['execute']):
        assert x['before_digest']==y['before_digest'] and x['observation']==y['observation']
        if x['action']!=y['action']:first=x['step'];break
        assert x['after_digest']==y['after_digest'];equal+=1
    summary['coupling'].append(dict(game=game,shared_prefix_actions=equal,first_action_divergence=first))
    audit=read(root/(game+'_action_audit.json'));rows=audit['records']
    summary['action_audits'][game]=dict(counterfactuals=len(rows),replays=audit['prefix_transition_checks'],
        removed_feedback_error=sum(r['proposed_feedback_error'] and not r['actual_feedback_error'] for r in rows),
        introduced_feedback_error=sum(r['actual_feedback_error'] and not r['proposed_feedback_error'] for r in rows),
        both_feedback_error=sum(r['actual_feedback_error'] and r['proposed_feedback_error'] for r in rows),
        immediate_score_better=sum(r['actual_quest_gain']>r['proposed_quest_gain'] for r in rows),
        immediate_score_worse=sum(r['actual_quest_gain']<r['proposed_quest_gain'] for r in rows))
    (out/(game+'_action_audit.json')).write_bytes((root/(game+'_action_audit.json')).read_bytes())
summary['usage']={k:sum(u[k] for u in usages) for k in ('requests','successful_responses','peak_usd_estimate','unknown_charge_attempts','prompt_tokens','completion_tokens')}
summary['replays']=sum(r['replays'] for r in summary['rows'])
summary['tests']=dict(passed=19,new_mechanism=11,previous_foundation=8)
(out/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(out/'cards.json').write_text(json.dumps(case_records,ensure_ascii=False,indent=2))
for name in ('source_manifest.json',): (out/name).write_bytes((root/'frozen'/name).read_bytes())
(out/'probe_audit.json').write_bytes((root/'probe_audit.json').read_bytes())
(out/'startup_failed_manifest.json').write_bytes((failed/'frozen/source_manifest.json').read_bytes())
files=[]
for top in ('frozen','evaluation','summary'):
    for path in (root/top).rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(root)
        if any(x in relative.parts for x in ('environment','replay','__pycache__','shared_api')):continue
        if path.suffix not in ('.py','.txt','.json','.jsonl','.gz','.log'):continue
        files.append((path,relative.as_posix()))
for path in root.glob('*.log'):files.append((path,path.name))
for path in failed.glob('*.log'):files.append((path,'startup_failure/'+path.name))
files.append((failed/'frozen/source_manifest.json','startup_failure/source_manifest.json'))
files.append((failed/'frozen/scar_public/experiments/sentry_persistent_trial.py','startup_failure/sentry_persistent_trial.py'))
for name in ('launch_sentry_persistent.py','audit_sentry_persistent_probe.py','audit_sentry_persistent_actions.py','collect_sentry_persistent.py'):
    files.append((Path('/root')/name,'evaluators/'+name))
secrets=re.findall(r'sk-[A-Za-z0-9_-]+',Path('/root/scar_research_20261015/private/deepseek.key').read_text())
for path,name in files:
    data=gzip.decompress(path.read_bytes()) if name.endswith('.json.gz') else path.read_bytes()
    assert all(s.encode() not in data for s in secrets),'Secret scan failed'
archive=root/'public_evidence.tgz'
with tarfile.open(archive,'w:gz') as tar:
    for path,name in files:tar.add(path,arcname=name)
receipt=dict(files=len(files),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    api_key_scan='passed',private_snapshots='excluded',baseline_archive_sha256='a04970c6c8370f407b2ed6c6c7e63616b7f96bbfde941ee3de33bab52284ab31')
(out/'public_evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
with tarfile.open(root/'summary.tgz','w:gz') as tar:tar.add(out,arcname='summary')
print(json.dumps(dict(rows=[{k:r[k] for k in ('game','mode','scores','repair_calls','status_counts','changed_actions','invalid_cards')} for r in summary['rows']],usage=summary['usage'],receipt=receipt)))
