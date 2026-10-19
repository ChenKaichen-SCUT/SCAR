import json
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018')
path=R/'feedback_status.json'
state=json.loads(path.read_text()) if path.exists() else {'status':'not_started'}
for run_id,entry in state.get('runs',{}).items():
    if entry.get('pid'):
        proc=Path('/proc')/str(entry['pid'])/'cmdline'
        entry['process_active']=proc.exists() and b'eval_feedback.py' in proc.read_bytes()
    audit=R/'control_audit'/f'{run_id}.jsonl'
    if audit.exists():
        rows=[json.loads(l) for l in audit.read_text().splitlines() if l.strip()]
        decisions=[r for r in rows if r['event']=='decision']
        entry['controller_reviews']=sum(r['event']=='controller' for r in rows)
        entry['repairs']=sum(r['event']=='repair' for r in rows)
        entry['last_decision']=decisions[-1]['action'] if decisions else None
print(json.dumps(state))
