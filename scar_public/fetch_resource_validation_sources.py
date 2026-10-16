"""Fetch only the two pinned public archives needed by the resource study."""
from pathlib import Path
from hashlib import sha256
import argparse,urllib.request
from scar_public.fresh_resource_suite import URL,ARCHIVE_SHA
from scar_public.contingent_benchmarks import fetch_archive


def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);a=p.parse_args()
    a.cache.mkdir(parents=True,exist_ok=True)
    fetch_archive(a.cache/'contff-tests.tgz')
    path=a.cache/'DeadendDomains.zip'
    if not path.exists():
        blob=urllib.request.urlopen(URL,timeout=45).read()
        assert sha256(blob).hexdigest()==ARCHIVE_SHA,'Public archive changed'
        path.write_bytes(blob)
    assert sha256(path.read_bytes()).hexdigest()==ARCHIVE_SHA
    print('Both public source archives verified.')


if __name__=='__main__':main()
