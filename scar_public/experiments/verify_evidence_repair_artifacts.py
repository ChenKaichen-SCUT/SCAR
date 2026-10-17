"""Check downloaded public evidence, execution provenance and matched starts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();root=a.directory
    receipt=json.loads((root/'evidence_receipt.json').read_text())
    archive=root/'public_evidence.tgz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['archive_sha256']
    with tarfile.open(archive) as z:
        members={m.name:m for m in z.getmembers() if m.isfile()}
        assert set(members)==set(receipt['members'])
        for name,expected in receipt['members'].items():
            assert not name.endswith('.pkl') and '/private/' not in name
            data=z.extractfile(members[name]).read()
            assert hashlib.sha256(data).hexdigest()==expected
            assert not re.search(rb'sk-[A-Za-z0-9_-]{20,}',data)
    source_members={}
    for name,key in [('original_source.tgz','original_source_sha256'),('followup_source.tgz','followup_source_sha256'),
                     ('carried_source.tgz','carried_repair_source_sha256')]:
        path=root/name;assert hashlib.sha256(path.read_bytes()).hexdigest()==receipt[key]
        with tarfile.open(path) as z:
            manifest=json.load(z.extractfile('source_manifest.json'))
            for member,sha in manifest.items():
                data=z.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==sha
                assert not re.search(rb'sk-[A-Za-z0-9_-]{20,}',data)
            source_members[name]=len(manifest)
    d=json.loads((root/'analysis.json').read_text());assert d['all_complete'] and len(d['runs'])==12
    matched={}
    for game in ('mark','metropolis','remnant'):
        runs=[r for r in d['runs'] if r['game']==game]
        assert len(runs)==4 and len({r['manifest']['initial_snapshot_sha256'] for r in runs})==1
        matched[game]=len({r['first_request_hash'] for r in runs})==1
    result=dict(verified_public_members=len(receipt['members']),verified_source_members=source_members,
                matched_initial_snapshots=True,identical_initial_request_by_game=matched,
                complete_prospective_runs=12,complete_followups=len(d['followups']),
                all_requests_have_usage=d['unknown_charge_attempts']==0,
                no_credential_patterns_or_private_checkpoints=True)
    (root/'artifact_verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
