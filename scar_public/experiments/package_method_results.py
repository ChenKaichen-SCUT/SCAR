"""Public traces, audits and source hashes only; never secrets or pickle states."""
import argparse,hashlib,json,re,tarfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
    analysis=json.loads((root/'analysis.json').read_text());assert analysis['all_complete']
    files=[root/n for n in ('analysis.json','native/result.json','ablations/result.json','logs/tests.log',
        'code/source_manifest.json','validate_method_repair.py','ablate_method_repair.py','analyze.py',
        'launch.sh','launch_full.sh','package.py','final_code/source_manifest.json',
        'final_native/result.json','logs/final_tests.log','benchmark.py','review_cost.json')]
    for status in sorted((root/'runtime').glob('*/*/*/current.json')):
        assert json.loads(status.read_text())['complete']
        run=status.parent
        files.extend(run/n for n in ('current.json','manifest.json','api/attempts.jsonl'))
        files.extend(sorted((run/'trace').glob('*.json')))
    files.extend(sorted((root/'runtime/initial').glob('*/manifest.json')))
    hashes={}
    with tarfile.open(root/'public_evidence.tgz','w:gz') as archive:
        for path in files:
            name=path.relative_to(root).as_posix();data=path.read_bytes()
            if re.search(rb'sk-[A-Za-z0-9_-]{20,}',data):raise RuntimeError('Possible secret in '+name)
            hashes[name]=hashlib.sha256(data).hexdigest();archive.add(path,arcname=name)
    receipt=dict(members=hashes,archive_sha256=hashlib.sha256((root/'public_evidence.tgz').read_bytes()).hexdigest(),
        archive_bytes=(root/'public_evidence.tgz').stat().st_size,
        source_sha256=hashlib.sha256((root/'source.tgz').read_bytes()).hexdigest(),
        final_source_sha256=hashlib.sha256((root/'final_source.tgz').read_bytes()).hexdigest(),
        credentials_or_checkpoints_included=False)
    (root/'evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:v for k,v in receipt.items() if k!='members'}))

if __name__=='__main__':main()
