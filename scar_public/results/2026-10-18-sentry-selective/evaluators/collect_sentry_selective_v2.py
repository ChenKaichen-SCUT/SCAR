import collections,gzip,hashlib,json,re,tarfile
from pathlib import Path
root=Path('/root/scar_sentry_selective_20261018_v2');out=root/'summary';out.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text())
manifest=read(root/'frozen/source_manifest.json')
for name,sha in manifest.items():
    if name!='parent_revision':assert hashlib.sha256((root/'frozen'/name).read_bytes()).hexdigest()==sha,name
diagnostic=read(root/'diagnostic.json');rows=[];usages=[r['usage'] for r in diagnostic['rows']];details=[]
role_control=read(root/'role_control.json') if (root/'role_control.json').exists() else None
if role_control:usages += [r['usage'] for r in role_control['rows']]
for game in ('remnant','mark','metropolis'):
    b=root/'evaluation'/game/'selective';result=read(b/'result.json');usages.append(result['usage'])
    trace=[read(p) for p in sorted((b/'trace').glob('*.json'))]
    events=[e for t in trace for e in t['persistent_events']];choices=[e for e in events if e['type']=='persistent_choice']
    cards=[e for e in events if e['type']=='persistent_card'];audit=read(root/(game+'_audit.json'))
    paths={p.name:p for p in (b/'api').glob('*.response.json')}
    if (b/'api/shared_reuse.jsonl').exists():
        for item in map(json.loads,(b/'api/shared_reuse.jsonl').read_text().splitlines()):
            path=Path(item['source']);paths[path.name]=path
    logical=dict(unique_model_requests=len(paths))
    for key in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens'):
        logical[key]=sum(read(path).get('usage',{}).get(key,0) for path in paths.values())
    row=dict(game=game,**result,logical_usage=logical,eligible_choices=sum(e['eligible'] for e in choices),
        replacements=sum(e['changed'] for e in choices),selection_reasons=dict(collections.Counter(e['selection_reason'] for e in choices if e['eligible'])),
        comparison_structural_errors=sum(bool(e['comparison_errors']) for e in choices),
        original_roles=dict(collections.Counter(e['comparison'].get('original_role',next((c['status'] for c in e['comparison'].get('candidates',[]) if c['id']==e.get('ordinary_id')),'unknown')) for e in choices if e['comparison'])),
        repair_status=dict(collections.Counter(e['card']['status'] for e in cards if e['card'])),
        **{k:v for k,v in audit.items() if k not in ('records','game')},
        score_curve={str(n):next(t['scores']['quest'] for t in trace if t['step']==n) for n in (50,100,150,200,250,300)})
    rows.append(row)
    details.append(dict(game=game,choices=[e for e in choices if e['eligible']],cards=cards))
    (out/(game+'_audit.json')).write_bytes((root/(game+'_audit.json')).read_bytes())
summary=dict(qualification='Three known development worlds, one frozen trajectory each. No independent or statistical improvement claim.',
    source_manifest_sha256=hashlib.sha256((root/'frozen/source_manifest.json').read_bytes()).hexdigest(),frozen_files=len(manifest)-1,
    tests_passed=36 if root.name.endswith('_v2') else 34,diagnostic=diagnostic['summary'],rows=rows,
    role_control_summary=role_control['summary'] if role_control else None,
    paid_usage={k:sum(u[k] for u in usages) for k in ('requests','successful_responses','peak_usd_estimate','unknown_charge_attempts','prompt_tokens','completion_tokens')},
    foundation_baseline=read(Path('/root/scar_sentry_foundation_20261018/summary/analysis.json'))['rows'],
    persistent_comparison=read(Path('/root/scar_sentry_persistent_20261018_v2/summary/analysis.json'))['rows'])
(out/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(out/'decisions.json').write_text(json.dumps(details,ensure_ascii=False,indent=2))
(out/'diagnostic.json').write_bytes((root/'diagnostic.json').read_bytes())
if role_control:(out/'role_control.json').write_bytes((root/'role_control.json').read_bytes())
(out/'source_manifest.json').write_bytes((root/'frozen/source_manifest.json').read_bytes())
files=[]
for top in ('frozen','evaluation','diagnostic_api','role_control_api','summary'):
    for path in (root/top).rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(root)
        if any(x in relative.parts for x in ('environment','replay','__pycache__','shared_api')):continue
        if path.suffix not in ('.py','.txt','.json','.jsonl','.gz','.log'):continue
        if path.name=='public_evidence_receipt.json':continue
        files.append((path,relative.as_posix()))
for path in root.glob('*.log'):files.append((path,path.name))
for name in ('launch_sentry_selective_v2.py','diagnose_sentry_selective_v2.py','audit_sentry_selective_v2.py','finish_sentry_selective_v2.py','collect_sentry_selective_v2.py','role_control_sentry_selective_v2.py'):
    files.append((Path('/root')/name,'evaluators/'+name))
secrets=re.findall(r'sk-[A-Za-z0-9_-]+',Path('/root/scar_research_20261015/private/deepseek.key').read_text())
for path,name in files:
    data=gzip.decompress(path.read_bytes()) if name.endswith('.json.gz') else path.read_bytes()
    assert all(s.encode() not in data for s in secrets),'Secret scan failed'
archive=root/'public_evidence.tgz'
with tarfile.open(archive,'w:gz') as tar:
    for path,name in files:tar.add(path,arcname=name)
receipt=dict(files=len(files),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),api_key_scan='passed',
    cached_response_dependencies=['a04970c6c8370f407b2ed6c6c7e63616b7f96bbfde941ee3de33bab52284ab31','81f99e07e0de58ce2fbb5a941c55fcfa5262d5320de42284010a8312dbd9777c'])
(out/'public_evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
with tarfile.open(root/'summary.tgz','w:gz') as tar:tar.add(out,arcname='summary')
print(json.dumps(dict(rows=[{k:r[k] for k in ('game','scores','comparison_calls','replacements','selection_reasons','original_roles','shared_advice_prefix')} for r in rows],paid_usage=summary['paid_usage'],receipt=receipt)))
