"""Public evidence only, with per-member hashes and credential-pattern checks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
    files=[root/n for n in ('analysis.json','scope_final.json','validation/results.json',
        'logs/tests.log','logs/followup_tests.log','logs/carried_tests.log','logs/carried_repair_tests.log',
        'code/source_manifest.json','followup_code/source_manifest.json','carried_code/source_manifest.json',
        'carried_repair_code/source_manifest.json','carried_validation/results.json','carried_repair_validation/results.json',
        'analyze.py','audit_scope.py','validate.py','package.py','audit_regret.py','profile_regret.json')]
    for run in sorted((root/'runtime').glob('*/*/*/current.json')):
        status=json.loads(run.read_text());assert status['complete']
        files.extend(run.parent/n for n in ('current.json','manifest.json','api/attempts.jsonl'))
        files.extend(sorted((run.parent/'trace').glob('*.json')))
    files.extend(sorted((root/'runtime/initial').glob('*/manifest.json')))
    hashes={}
    with tarfile.open(root/'public_evidence.tgz','w:gz') as archive:
        for path in files:
            data=path.read_bytes()
            if re.search(rb'sk-[A-Za-z0-9_-]{20,}',data):raise RuntimeError('Possible credential in '+path.name)
            name=path.relative_to(root).as_posix();hashes[name]=hashlib.sha256(data).hexdigest()
            archive.add(path,arcname=name)
    receipt=dict(members=hashes,archive_sha256=hashlib.sha256((root/'public_evidence.tgz').read_bytes()).hexdigest(),
        archive_bytes=(root/'public_evidence.tgz').stat().st_size,
        original_source_sha256=hashlib.sha256((root/'source.tgz').read_bytes()).hexdigest(),
        followup_source_sha256=hashlib.sha256((root/'followup_source.tgz').read_bytes()).hexdigest(),
        carried_repair_source_sha256=hashlib.sha256((root/'carried_repair_source.tgz').read_bytes()).hexdigest(),
        credentials_or_checkpoints_included=False)
    (root/'evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:v for k,v in receipt.items() if k!='members'}))

if __name__=='__main__':main()
