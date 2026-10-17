"""Archive only executable source and this experiment's protocol."""
import hashlib,io,json,re,tarfile
from pathlib import Path

def main():
    root=Path.cwd();out=root.parent/'action_repair_source.tgz';manifest={}
    names=sorted({p for directory in ('scar','scar_public') for p in (root/directory).rglob('*.py')
                  if '__pycache__' not in p.parts})
    names.append(root/'scar_public/experiments/action_repair_protocol.txt')
    with tarfile.open(out,'w:gz') as archive:
        for p in names:
            data=p.read_bytes();name=p.relative_to(root).as_posix()
            if re.search(rb'sk-[A-Za-z0-9_-]{20,}',data):raise ValueError('Possible secret in '+name)
            manifest[name]=hashlib.sha256(data).hexdigest()
            info=tarfile.TarInfo(name);info.size=len(data);archive.addfile(info,io.BytesIO(data))
        data=json.dumps(manifest,sort_keys=True,indent=2).encode();info=tarfile.TarInfo('source_manifest.json')
        info.size=len(data);archive.addfile(info,io.BytesIO(data))
    print(json.dumps(dict(path=str(out),files=len(manifest),sha256=hashlib.sha256(out.read_bytes()).hexdigest())))

if __name__=='__main__':main()
