"""Freeze executable source before paid evaluation; no key/checkpoint inclusion."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

def main():
    root=Path.cwd();out=root.parent/'evidence_repair_source.tgz'
    names=set(subprocess.check_output(['git','ls-files'],text=True).splitlines())
    names.update(['scar_public/evidence_repair.py','scar_public/test_evidence_repair.py',
        'scar_public/experiments/validate_carried_repair.py',
        'scar_public/experiments/evidence_repair_protocol.txt',
        'scar_public/experiments/evidence_scope_followup.txt',
        'scar_public/experiments/launch_evidence_repair.sh'])
    names=sorted(n for n in names if (root/n).is_file() and
        (n.endswith(('.py','.sh')) or n.endswith(('evidence_repair_protocol.txt','evidence_scope_followup.txt'))))
    manifest={}
    with tarfile.open(out,'w:gz') as z:
        for name in names:
            data=(root/name).read_bytes()
            if re.search(rb'sk-[A-Za-z0-9_-]{20,}',data):raise RuntimeError('Possible credential in '+name)
            manifest[name]=hashlib.sha256(data).hexdigest()
            info=tarfile.TarInfo(name);info.size=len(data);z.addfile(info,io.BytesIO(data))
        data=json.dumps(manifest,indent=2).encode();info=tarfile.TarInfo('source_manifest.json')
        info.size=len(data);z.addfile(info,io.BytesIO(data))
    print(json.dumps(dict(path=str(out),files=len(manifest),sha256=hashlib.sha256(out.read_bytes()).hexdigest())))

if __name__=='__main__':main()
