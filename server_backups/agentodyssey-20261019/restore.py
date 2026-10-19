"""Verify every chunk and archived file; optionally restore into a new directory."""
import argparse,hashlib,io,json,shutil,tarfile
from pathlib import Path,PurePosixPath

class Chunks(io.RawIOBase):
    def __init__(self,paths):self.paths=iter(paths);self.current=None
    def readable(self):return True
    def readinto(self,b):
        while True:
            if self.current is None:
                try:self.current=next(self.paths).open('rb')
                except StopIteration:return 0
            n=self.current.readinto(b)
            if n:return n
            self.current.close();self.current=None
    def close(self):
        if self.current:self.current.close()
        super().close()

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--verify-only',action='store_true');g.add_argument('--destination',type=Path)
    args=parser.parse_args();root=Path(__file__).resolve().parent
    meta=json.loads((root/'metadata/chunks.json').read_text());manifest=json.loads((root/'metadata/manifest.json').read_text())
    paths=[];whole=hashlib.sha256()
    for x in meta['chunks']:
        p=root/'archive'/x['file'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256'],p
        paths.append(p)
        with p.open('rb') as f:
            for b in iter(lambda:f.read(8*1024*1024),b''):whole.update(b)
    assert whole.hexdigest()==meta['archive_sha256'],'Combined archive checksum mismatch'
    if args.destination:
        assert not args.destination.exists(),'Destination must not already exist'
        args.destination.mkdir(parents=True)
    expected={x['path']:x for x in manifest['included']};seen=set();count=0
    with io.BufferedReader(Chunks(paths)) as stream,tarfile.open(fileobj=stream,mode='r|gz') as tar:
        for member in tar:
            path=PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts and path.parts[0] in ['workspace','restore'],member.name
            h=hashlib.sha256();length=0;dest=None
            if args.destination:
                target=args.destination.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True);dest=target.open('xb')
            try:
                with tar.extractfile(member) as f:
                    for b in iter(lambda:f.read(1024*1024),b''):
                        h.update(b);length+=len(b)
                        if dest:dest.write(b)
            finally:
                if dest:dest.close()
            if path.parts[0]=='workspace':
                rel='/'.join(path.parts[1:]);assert rel in expected and rel not in seen
                assert h.hexdigest()==expected[rel]['sha256'] and length==expected[rel]['bytes'],rel
                seen.add(rel)
            count+=1
    assert seen==set(expected),'Manifest and archive differ'
    print(json.dumps({'verified_files':len(seen),'archive_members':count,'archive_sha256':whole.hexdigest(),'restored_to':str(args.destination) if args.destination else None}))

if __name__=='__main__':main()
