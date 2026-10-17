"""Verify portable result/source archives against receipts, without extraction."""
import argparse,hashlib,json,tarfile
from pathlib import Path

def source(path):
    with tarfile.open(path) as archive:
        manifest=json.load(archive.extractfile('source_manifest.json'))
        for name,expected in manifest.items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest()==expected,name
    return len(manifest)

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
    receipt=json.loads((root/'evidence_receipt.json').read_text())
    for name,key in (('public_evidence.tgz','archive_sha256'),('source.tgz','source_sha256'),('final_source.tgz','final_source_sha256')):
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==receipt[key],name
    with tarfile.open(root/'public_evidence.tgz') as archive:
        assert set(archive.getnames())==set(receipt['members'])
        for name,expected in receipt['members'].items():
            assert not name.endswith(('.pkl','.key','.clixml'))
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest()==expected,name
    report=dict(public_members=len(receipt['members']),paid_source_files=source(root/'source.tgz'),
                final_source_files=source(root/'final_source.tgz'),all_hashes_match=True)
    (root/'artifact_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
