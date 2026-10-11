"""Event-driven postprocessing. Wait for runner exit with pidfd, not polling.

No new API calls or automatic experimental reruns. Incomplete runs produce an
explicit partial report and remain incomplete; no result is fabricated.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import sys
from scar.io import atomic_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--wait-pid',type=int)
    a=p.parse_args();root=Path(a.runtime)
    if a.wait_pid:
        try:
            fd=os.pidfd_open(a.wait_pid)
        except ProcessLookupError:
            fd=None
        if fd is not None:
            select.select([fd],[],[]);os.close(fd)
    commands=[['scar_sequence.audit_details'],['scar_sequence.export_initials'],['scar_sequence.resource_audit','--runtime',str(root)],['scar_sequence.analyze','--runtime',str(root)],
              ['scar_sequence.verify','--runtime',str(root)],['scar_sequence.mechanism_cases','--runtime',str(root)],['scar_sequence.report']]
    for args in commands:
        result=subprocess.run([sys.executable,'-m',*args])
        if result.returncode:
            atomic_json(root/'progress.json',{'phase':'postprocessing_failed','module':args[0],
                'returncode':result.returncode,'api_reruns':0})
            raise SystemExit(result.returncode)
    verification=json.loads(Path('results/sequence/verification.json').read_text())
    files=sorted([p for base in ['scar_sequence','results/sequence','reports/sequence'] for p in Path(base).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact_manifest.json'])
    files += [Path('configs/protocol_sequence.json'),Path('tests/test_sequence.py')]
    atomic_json('results/sequence/artifact_manifest.json',{'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
         'verification_passed':verification['passed'],'no_downloaded_engine_or_models':True})
    atomic_json(root/'progress.json',{'phase':'completed_verified_ready_to_publish' if verification['passed'] else 'incomplete_or_verification_failed',
        'verification_passed':verification['passed'],'episodes':verification['episodes_replayed'],
        'new_cost_usd':verification['new_ledger_usd'],'project_total_usd':verification['project_total_usd'],
        'report':'reports/sequence/实验报告.md','api_reruns':0})


if __name__=='__main__':main()
