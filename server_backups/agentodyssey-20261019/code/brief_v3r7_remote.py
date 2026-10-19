import json,hashlib
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');rid='remnant__v3r7_300_20261019'
def rows(p):
    data=[]
    if p.exists():
        for line in p.read_text().splitlines():
            try:data.append(json.loads(line))
            except json.JSONDecodeError:pass
    return data
s=json.loads((R/'feedback_v3r7_300_status.json').read_text());r=rows(R/'runs'/rid/'agent_adam_davis/agent_log.jsonl');a=rows(R/'telemetry'/rid/'api_calls.jsonl')
d=rows(R/'control_audit'/f'{rid}.jsonl');dec=[x for x in d if x.get('event')=='decision']
out={'phase':s['phase'],'status':s['runs'][rid]['status'],'steps':len(r),'score':sum(x['reward'].get('quest',0) for x in r),'gains':[x['step']+1 for x in r if x['reward'].get('quest',0)],'deaths':[x['step']+1 for x in r if 'I have died.' in x['next_observation']['text']],'api_completed':sum(x.get('event')=='completed' for x in a),'api_errors':[x for x in a if x.get('event') not in ['started','completed']],'last_actions':[(x['step']+1,x['action']) for x in r[-4:]],'advisory_overrides':sum(any(w['kind']=='task_no_progress_requires_reassessment' for w in x['check'].get('warnings',[])) for x in dec),'report_ready':(R/'feedback_v3r7_300_analysis.json').exists()}
print(json.dumps(out,ensure_ascii=False))
