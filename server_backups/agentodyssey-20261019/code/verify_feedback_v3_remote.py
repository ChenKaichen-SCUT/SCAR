"""Verify initial launch, frozen source, processes and telemetry; no inference."""
import hashlib,json,shutil
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');proto=json.loads((R/'protocol_feedback_v3.json').read_text())
hashes={n:hashlib.sha256((R/n).read_bytes()).hexdigest()==digest for n,digest in proto['implementation_sha256'].items()}
assert all(hashes.values())
for n in ['feedback_v3_agent.py','feedback_v3_core.py']:
    assert hashlib.sha256((R/'agentodyssey/agents'/n).read_bytes()).hexdigest()==proto['implementation_sha256'][n]
state=json.loads((R/'feedback_v3_status.json').read_text());out={'frozen_hashes_match':True,'free_disk_gb':round(shutil.disk_usage(R).free/1024**3,2),'runs':{}}
for g in proto['games']:
    rid=g+'__feedback_v3';rs=state['runs'].get(rid,{});p=Path('/proc')/str(rs.get('pid'))/'cmdline'
    row={'status':rs.get('status'),'steps':rs.get('steps'),'process_alive':p.exists(),'api':{}}
    for suffix in ['', '__controller']:
        f=R/'telemetry'/(rid+suffix)/'api_calls.jsonl';events=[json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
        row['api'][suffix or 'actor']={k:sum(e['event']==k for e in events) for k in ['started','completed','error']}
    out['runs'][g]=row
print(json.dumps(out))
