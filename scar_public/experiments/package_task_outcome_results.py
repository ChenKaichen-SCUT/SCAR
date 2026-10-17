"""Publish all task-success development evidence, excluding private snapshots."""
import argparse,hashlib,json,re,tarfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
    files=[root/n for n in ('analysis.json','diagnosis.json','dry_audit.json','dry_audit_v2.json','tests.txt','tests_v2.txt',
        'final_tests.txt','final_replay.json','launch.sh','launch_v2.sh','analyze_task_outcome.py','diagnose_task_outcome.py')]
    sources={}
    for code,archive in (('code','source.tgz'),('code_v2','source_v2.tgz'),('final_code','final_source.tgz')):
        manifest=json.loads((root/code/'source_manifest.json').read_text())
        assert all(hashlib.sha256((root/code/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
        sources[archive]=dict(sha256=hashlib.sha256((root/archive).read_bytes()).hexdigest(),verified_files=len(manifest))
        files.extend((root/archive,root/code/'source_manifest.json'))
    for version,arms in (('full',('v14','v15')),('corrected',('v15',))):
        for game in ('remnant','mark','metropolis'):
            run=root/version/game
            files.extend(run/name for name in ('manifest.json','usage.json','provider_calls.jsonl','external_cache.jsonl','api/attempts.jsonl','api/reuse.jsonl') if (run/name).exists())
            for arm in arms:
                path=run/arm/'current.json';assert json.loads(path.read_text())['complete']
                files.append(path);files.extend(sorted((run/arm/'trace').glob('*.json')))
    hashes={}
    with tarfile.open(root/'public_evidence.tgz','w:gz') as archive:
        for path in files:
            name=path.relative_to(root).as_posix();data=path.read_bytes()
            if path.suffix!='.tgz':assert not re.search(rb'sk-[A-Za-z0-9_-]{20,}',data),name
            hashes[name]=hashlib.sha256(data).hexdigest();archive.add(path,arcname=name)
    receipt=dict(members=hashes,sources=sources,archive_sha256=hashlib.sha256((root/'public_evidence.tgz').read_bytes()).hexdigest(),
        credentials_or_engine_checkpoints_included=False,experiments='Six initial development trajectories plus three corrected V15 trajectories; V14 controls reused once')
    (root/'evidence_receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:v for k,v in receipt.items() if k!='members'}))


if __name__=='__main__':main()
