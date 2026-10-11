"""Check unchanged experiments, original providers' logs, and diagnostic freezes."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from scar.io import atomic_json,digest


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--output',default='results/v3/attribution');args=p.parse_args()
    runtime=Path(args.runtime);out=Path(args.output)
    freeze=json.loads((runtime/'execution_freeze.json').read_text())
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert all(sha(p)==v for p,v in freeze['files'].items())
    protected={p:v for p,v in freeze['protected_files'].items() if p!='README.md'}
    assert all(sha(p)==v['sha256'] for p,v in protected.items())
    assert all(sha(p)==v for p,v in freeze['api_request_files'].items())
    assert not list(runtime.rglob('requests.jsonl'))
    with sqlite3.connect('file:/root/scar_workspace/runtime/budget.sqlite?mode=ro',uri=True) as db:
        total=db.execute('SELECT COALESCE(SUM(COALESCE(charged,reserved)),0) FROM requests').fetchone()[0]
        pending=db.execute("SELECT COUNT(*) FROM requests WHERE status='reserved'").fetchone()[0]
    assert abs(total-freeze['preexisting_project_cost_usd'])<1e-8
    assert pending==0
    protocol=json.loads((out/'protocol.json').read_text());states=json.loads((out/'state_manifest.json').read_text())
    hashes=json.loads((out/'protocol_freeze.json').read_text())
    assert digest(protocol)==hashes['protocol_sha256']==freeze['protocol_sha256']
    assert digest(states)==hashes['state_list_sha256']
    results=[json.loads((runtime/'branches'/(s['state_id']+'.json')).read_text()) for s in states]
    for r in results:
        assert r['api_calls']==0 and r['protocol_search']==protocol['search']
        for b in r['branches'].values():
            assert b['verified']==bool(b['verification'] and b['verification']['verified'])
            if b['verified']:assert b['distance']==len(b['path']) and b['verification']['steps'][-1]['physical_goal']
    checks={'protected_repository_files_unchanged':len(protected),'frozen_diagnostic_code_unchanged':True,'frozen_state_list_unchanged':True,'original_request_logs_unchanged':len(freeze['api_request_files']),'new_request_logs':0,'project_cumulative_usd':total,'pending_api_reservations':pending,'states_verified':len(results),'api_calls':0,'api_cost_usd':0,'scope':'Original results and policy unchanged; README may add the new report link.'}
    atomic_json(out/'integrity_checks.json',checks);print(json.dumps(checks))


if __name__=='__main__':main()
