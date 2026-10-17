"""Package only public traces/audits and source provenance; never checkpoints or keys."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
    paths=[root/'source_manifest.json',root/'llm_results.json',root/'logs/tests.log',
           root/'historical_checks/results.json',root/'llm_veto_checks/results.json']
    paths += [root/'frozen_corrected'/n for n in ('summary.json','control/result.json','reuse/result.json')]
    for arm in ('control','reuse'):
        directory=root/'runtime'/('llm_'+arm)/'evidence_decision_v10/metropolis'
        current=json.loads((directory/'current.json').read_text());assert current['complete']
        paths += [directory/n for n in ('current.json','manifest.json','api/attempts.jsonl')]
        paths += sorted((directory/'trace').glob('*.json'))
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with tarfile.open(root/'public_evidence.tgz','w:gz') as archive:
        for path in paths:archive.add(path,arcname=str(path.relative_to(root)))
    receipt=dict(files=len(paths),members=hashes,
        archive_sha256=hashlib.sha256((root/'public_evidence.tgz').read_bytes()).hexdigest(),
        archive_bytes=(root/'public_evidence.tgz').stat().st_size,
        llm_source_archive_sha256=hashlib.sha256((root/'llm_code.tgz').read_bytes()).hexdigest(),
        no_checkpoint_or_credential_files=True)
    (root/'evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:v for k,v in receipt.items() if k!='members'}))


if __name__=='__main__':main()
