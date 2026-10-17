"""Export public traces/source/audits; never export hidden environment snapshots."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile

from scar.io import atomic_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--previous',type=Path,required=True);p.add_argument('--key',type=Path,required=True)
    p.add_argument('--control',type=Path)
    a=p.parse_args()
    secrets=[s.encode() for s in re.findall(r'sk-[A-Za-z0-9_-]+',a.key.read_text())]
    entries=[]
    roots=[('revision1',a.previous),('revision2',a.root)]
    if a.control:roots.append(('generic_control',a.control))
    for label,root in roots:
        for name in ('plan.json','trigger_audit.json','analysis.json'):
            path=root/name
            if path.exists():entries.append((label+'/'+name,path))
        for path in (root/'frozen').rglob('*'):
            if path.is_file() and path.suffix in ('.py','.txt','.json') and '__pycache__' not in path.parts:
                entries.append((label+'/frozen/'+path.relative_to(root/'frozen').as_posix(),path))
        for path in (root/'controls').glob('remnant_r*.json'):
            if '.mismatch.' not in path.name:entries.append((label+'/controls/'+path.name,path))
        for block in (root/'branches').glob('*'):
            for name in ('manifest.json','result.json','environment_audit.json','fork_public_memory.json'):
                path=block/name
                if path.exists():entries.append((label+'/branches/'+block.name+'/'+name,path))
            for arm in ('off','advice','repair'):
                for path in (block/arm/'trace').glob('*.json'):
                    entries.append((label+'/branches/'+block.name+'/'+arm+'/trace/'+path.name,path))
            for path in (block/'api').glob('*'):
                if path.is_file() and path.name.endswith(('.json','.jsonl','.gz')):
                    entries.append((label+'/branches/'+block.name+'/api/'+path.name,path))
    manifest={}
    for name,path in entries:
        data=path.read_bytes();plain=gzip.decompress(data) if path.suffix=='.gz' else data
        assert all(secret not in plain for secret in secrets),'Secret detected; no export'
        assert not name.endswith('.pkl')
        manifest[name]=hashlib.sha256(data).hexdigest()
    atomic_json(a.root/'public_evidence_manifest.json',manifest)
    archive=a.root/'public_evidence.tgz'
    with tarfile.open(archive,'w:gz') as t:
        for name,path in entries:t.add(path,arcname=name)
        t.add(a.root/'public_evidence_manifest.json',arcname='manifest.json')
    receipt=dict(files=len(entries),bytes=archive.stat().st_size,
                 sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                 key_scan_passed=True,hidden_environment_snapshots=False)
    atomic_json(a.root/'public_evidence_receipt.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':main()
