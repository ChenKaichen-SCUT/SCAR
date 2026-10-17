"""Freeze V16 executable sources and protocol without credentials or snapshots."""
import hashlib, io, json, re, tarfile
from pathlib import Path


def main():
    root=Path.cwd(); out=root.parent/'task_progress_source.tgz'; manifest={}
    paths=sorted(p for d in ('scar','scar_public') for p in (root/d).rglob('*.py') if '__pycache__' not in p.parts)
    paths.append(root/'scar_public/experiments/task_progress_protocol.txt')
    paths.append(root/'scar_public/experiments/task_progress_amendment.txt')
    with tarfile.open(out,'w:gz') as t:
        for p in paths:
            b=p.read_bytes(); name=p.relative_to(root).as_posix()
            assert not re.search(rb'sk-[A-Za-z0-9_-]{20,}',b),name
            manifest[name]=hashlib.sha256(b).hexdigest(); item=tarfile.TarInfo(name); item.size=len(b); t.addfile(item,io.BytesIO(b))
        b=json.dumps(manifest,sort_keys=True,indent=2).encode(); item=tarfile.TarInfo('source_manifest.json'); item.size=len(b); t.addfile(item,io.BytesIO(b))
    print(json.dumps(dict(files=len(manifest),sha256=hashlib.sha256(out.read_bytes()).hexdigest())))


if __name__=='__main__':main()
