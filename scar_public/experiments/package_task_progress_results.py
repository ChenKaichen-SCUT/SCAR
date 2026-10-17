"""Package completed V16 development evidence without engine snapshots or keys."""
import argparse, hashlib, json, re, tarfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
    names=['analysis.json','diagnosis.json','dry_audit.json','tests.txt','tests_v2.txt','final_tests.txt',
           'final_replay.json','amendment.txt','analyze_task_progress.py','diagnose_task_progress.py']
    files=[root/n for n in names]; files.extend(sorted(root.glob('launch*.sh'))); sources={}
    for code,source in [('code','source.tgz'),('code_v2','source_v2.tgz'),('code_v3','source_v3.tgz'),('final_code','final_source.tgz')]:
        manifest=json.loads((root/code/'source_manifest.json').read_text())
        assert all(hashlib.sha256((root/code/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
        sources[source]=dict(sha256=hashlib.sha256((root/source).read_bytes()).hexdigest(),verified_files=len(manifest))
        files.extend([root/source,root/code/'source_manifest.json'])
    trajectories=0; actions=0
    for group in ('selected','selected_v2','full','ablation','corrected'):
        for path in sorted((root/group).glob('*/manifest.json')):
            run=path.parent; manifest=json.loads(path.read_text())
            files.extend(run/n for n in ('manifest.json','usage.json','provider_calls.jsonl','external_cache.jsonl','api/attempts.jsonl','api/reuse.jsonl') if (run/n).exists())
            for arm in manifest['arms']:
                status=run/arm/'current.json'; assert json.loads(status.read_text())['complete']
                files.append(status); rows=sorted((run/arm/'trace').glob('*.json')); files.extend(rows)
                trajectories+=1; actions+=len(rows)
    hashes={}
    with tarfile.open(root/'public_evidence.tgz','w:gz') as t:
        for p in files:
            b=p.read_bytes();name=p.relative_to(root).as_posix()
            if p.suffix!='.tgz':assert not re.search(rb'sk-[A-Za-z0-9_-]{20,}',b),name
            hashes[name]=hashlib.sha256(b).hexdigest();t.add(p,arcname=name)
    receipt=dict(members=hashes,sources=sources,trajectories=trajectories,environment_actions=actions,
        archive_sha256=hashlib.sha256((root/'public_evidence.tgz').read_bytes()).hexdigest(),
        credentials_or_engine_checkpoints_included=False,
        qualification='Keep selected-state development tests and defective-source runs separate from corrected full-game results')
    (root/'evidence_receipt.json').write_text(json.dumps(receipt,indent=2)); print(json.dumps({k:v for k,v in receipt.items() if k!='members'}))


if __name__=='__main__':main()
