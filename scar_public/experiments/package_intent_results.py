"""Package completed public evidence; omit credentials and engine checkpoints."""
import argparse,hashlib,json,re,tarfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
    files=[root/'analysis.json',root/'code/source_manifest.json',root/'launch.sh',root/'analyze_intent_pairs.py']
    manifest=json.loads((root/'code/source_manifest.json').read_text())
    assert all(hashlib.sha256((root/'code'/n).read_bytes()).hexdigest()==s for n,s in manifest.items())
    for pair in sorted((root/'pairs').iterdir()):
        files.extend(pair/n for n in ('manifest.json','usage.json','provider_calls.jsonl','api/attempts.jsonl'))
        for arm in ('observe','enforce'):
            status=pair/arm/'current.json';assert json.loads(status.read_text())['complete']
            files.append(status);files.extend(sorted((pair/arm/'trace').glob('*.json')))
    hashes={}
    with tarfile.open(root/'public_evidence.tgz','w:gz') as archive:
        for path in files:
            name=path.relative_to(root).as_posix();data=path.read_bytes()
            if re.search(rb'sk-[A-Za-z0-9_-]{20,}',data):raise ValueError('Possible credential in '+name)
            hashes[name]=hashlib.sha256(data).hexdigest();archive.add(path,arcname=name)
    result=dict(members=hashes,archive_sha256=hashlib.sha256((root/'public_evidence.tgz').read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256((root/'source.tgz').read_bytes()).hexdigest(),
        paid_source_files_verified=len(manifest),credentials_or_checkpoints_included=False)
    (root/'evidence_receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='members'}))

if __name__=='__main__':main()
