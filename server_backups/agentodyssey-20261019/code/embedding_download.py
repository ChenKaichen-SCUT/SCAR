import pathlib,json,urllib.request,hashlib,time,concurrent.futures
R=pathlib.Path(__file__).resolve().parent;meta=json.loads((R/'embedding_metadata.json').read_text())
out=R/'models/Qwen3-Embedding-0.6B';out.mkdir(parents=True,exist_ok=True)
def fetch(item):
 name=item['rfilename']
 if name in ['README.md','.gitattributes']:return
 p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
 url='https://hf-mirror.com/Qwen/Qwen3-Embedding-0.6B/resolve/'+meta['sha']+'/'+name
 h=hashlib.sha256() if item.get('lfs') else hashlib.sha1(b'blob '+str(item['size']).encode()+b'\x00')
 with urllib.request.urlopen(url,timeout=60) as response,p.with_suffix(p.suffix+'.partial').open('wb') as f:
  while True:
   b=response.read(4*1024*1024)
   if not b:break
   f.write(b);h.update(b)
 expected=item['lfs']['sha256'] if item.get('lfs') else item['blobId']
 assert h.hexdigest()==expected,(name,h.hexdigest(),expected)
 p.with_suffix(p.suffix+'.partial').replace(p);print(json.dumps({'downloaded':name,'bytes':p.stat().st_size,'digest':expected}),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(fetch,meta['siblings']))
(R/'embedding_ready.flag').write_text(meta['sha'])
