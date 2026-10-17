"""Freeze executable source and the prospective task-success protocol."""
import hashlib,io,json,re,tarfile
from pathlib import Path


def main():
    root=Path.cwd();out=root.parent/'task_outcome_source.tgz';manifest={}
    paths=sorted(p for directory in ('scar','scar_public') for p in (root/directory).rglob('*.py') if '__pycache__' not in p.parts)
    paths.append(root/'scar_public/experiments/task_outcome_protocol.txt')
    paths.append(root/'scar_public/experiments/task_outcome_amendment.txt')
    with tarfile.open(out,'w:gz') as archive:
        for path in paths:
            data=path.read_bytes();name=path.relative_to(root).as_posix()
            assert not re.search(rb'sk-[A-Za-z0-9_-]{20,}',data),name
            manifest[name]=hashlib.sha256(data).hexdigest();member=tarfile.TarInfo(name);member.size=len(data);archive.addfile(member,io.BytesIO(data))
        data=json.dumps(manifest,sort_keys=True,indent=2).encode();member=tarfile.TarInfo('source_manifest.json');member.size=len(data);archive.addfile(member,io.BytesIO(data))
    print(json.dumps(dict(files=len(manifest),sha256=hashlib.sha256(out.read_bytes()).hexdigest())))


if __name__=='__main__':main()
