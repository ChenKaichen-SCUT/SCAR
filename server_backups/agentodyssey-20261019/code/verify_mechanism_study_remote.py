import json,hashlib
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018')
result={}
for stem in ['runner_mechanism_study','proxy_mechanism_study']:
    f=R/(stem+'.pid');pid=int(f.read_text()) if f.exists() else None;p=Path('/proc')/str(pid)/'cmdline'
    result[stem]={'pid':pid,'running_expected_command':p.exists() and b'mechanism_study' in p.read_bytes()}
p=R/'mechanism_study_status.json';state=json.loads(p.read_text()) if p.exists() else {}
result['phase']=state.get('phase');result['runs']={rid:{k:r.get(k) for k in ['status','steps','main_quest','completion_reason','variant','selected_disabled_components','error']} for rid,r in state.get('runs',{}).items()}
proto=json.loads((R/'protocol_mechanism_study.json').read_text());result['code_hashes_match']=all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in proto['implementation_sha256'].items())
pre=json.loads((R/'mechanism_study_preflight.json').read_text());result['frozen_baselines_unchanged']=all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in pre['protected_files_unchanged'].items())
result['historical_reference_unchanged']=all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in proto['historical_reference_sha256'].items())
api={}
for rid in state.get('runs',{}):
    events=[]
    for suffix in ['', '__controller']:
        p=R/'telemetry'/(rid+suffix)/'api_calls.jsonl'
        if p.exists():
            for x in p.read_text().splitlines():
                try:events.append(json.loads(x))
                except json.JSONDecodeError:pass
    if events:api[rid]={'completed':sum(x.get('event')=='completed' for x in events),'errors':sum(x.get('event')=='error' for x in events)}
result['api']=api
(R/'mechanism_study_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
