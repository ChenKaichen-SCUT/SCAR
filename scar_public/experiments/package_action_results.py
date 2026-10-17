"""Archive completed public action-repair evidence, never private engine state."""
import argparse,hashlib,json,re,tarfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root
    files=[root/n for n in ('analysis.json','compatibility.json','exposure.json','native/result.json','server_tests.txt')]
    sources={}
    for code,archive_name in (('dev_code','native_source.tgz'),('code','source.tgz'),('code_v2','source_v2.tgz'),('code_v3','source_v3.tgz'),('final_code','final_source.tgz')):
        manifest=json.loads((root/code/'source_manifest.json').read_text())
        assert all(hashlib.sha256((root/code/n).read_bytes()).hexdigest()==s for n,s in manifest.items())
        sources[archive_name]=dict(sha256=hashlib.sha256((root/archive_name).read_bytes()).hexdigest(),verified_files=len(manifest))
        files.extend((root/archive_name,root/code/'source_manifest.json'))
    for version in ('pairs','pairs_v2','pairs_v3'):
        for game in ('metropolis','remnant'):
            pair=root/version/game
            files.extend(pair/n for n in ('manifest.json','usage.json','provider_calls.jsonl','external_cache.jsonl','api/attempts.jsonl') if (pair/n).exists())
            for arm in ('observe','execute'):
                status=pair/arm/'current.json';assert json.loads(status.read_text())['complete']
                files.append(status);files.extend(sorted((pair/arm/'trace').glob('*.json')))
    hashes={}
    with tarfile.open(root/'public_evidence.tgz','w:gz') as archive:
        for path in files:
            name=path.relative_to(root).as_posix();data=path.read_bytes()
            if path.suffix!='.tgz' and re.search(rb'sk-[A-Za-z0-9_-]{20,}',data):raise ValueError('Possible credential in '+name)
            hashes[name]=hashlib.sha256(data).hexdigest();archive.add(path,arcname=name)
    result=dict(members=hashes,archive_sha256=hashlib.sha256((root/'public_evidence.tgz').read_bytes()).hexdigest(),
        sources=sources,credentials_or_engine_checkpoints_included=False,
        final_code_relation='Final safeguards are replay-checked against all primary decisions; paid V3 retains its own immutable source archive')
    (root/'evidence_receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='members'}))


if __name__=='__main__':main()
