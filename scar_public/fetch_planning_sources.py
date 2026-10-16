"""Fetch pinned public inputs and the author's executable; never fetch credentials."""
import argparse
from hashlib import sha256
from pathlib import Path
import urllib.request,zipfile
from scar_public.contingent_benchmarks import SOURCE,ARCHIVE_SHA
from scar_public.benchmark_suite import CPOR_COMMIT

FILES={
 'Tests_doors5_d.pddl':'bd71538cc44f7937d4e7b735c79bc1aa7617dd7fd1f2dcbe371f1de9ff7c4fd0',
 'Tests_doors5_p.pddl':'d5446fb22a108548fe863ce683c30d1d7c50f3f836b258d1c6fae38f6a334008',
 'Tests_localize5_d.pddl':'c4ecb273b331a853bec49833dedec807167343eec98bd7a5bf63eeeb2536a2dd',
 'Tests_localize5_p.pddl':'aa601095a7bdba4d5a926d64d104008f7d6bb62f6e0dffde497cd91c4f649f14'}

def fetch(path,url,digest):
    data=path.read_bytes() if path.exists() else urllib.request.urlopen(url,timeout=60).read()
    if sha256(data).hexdigest()!=digest:raise ValueError('checksum mismatch: '+path.name)
    if not path.exists():path.write_bytes(data)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cache',type=Path);p.add_argument('--cff',action='store_true');a=p.parse_args()
    a.cache.mkdir(parents=True,exist_ok=True)
    fetch(a.cache/'contff-tests.tgz',SOURCE,ARCHIVE_SHA)
    for filename,digest in FILES.items():
        path=filename.replace('_','/')
        fetch(a.cache/filename,f'https://raw.githubusercontent.com/aiplan4eu/up-cpor/{CPOR_COMMIT}/{path}',digest)
    if a.cff:
        archive=a.cache/'Contingent-FF.zip'
        fetch(archive,'https://fai.cs.uni-saarland.de/hoffmann/ff/Contingent-FF.zip',
              '3e5b8785e9465ba6f95d9863c7351658615d3d8f2b482b66b24ef055478e5744')
        with zipfile.ZipFile(archive) as z:data=z.read('Contingent-FF')
        target=a.cache/'Contingent-FF';target.write_bytes(data);target.chmod(0o755)
    print('Pinned inputs verified.')
