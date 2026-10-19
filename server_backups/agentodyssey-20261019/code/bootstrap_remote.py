import pathlib,subprocess,urllib.request,json,hashlib,tarfile,zipfile,concurrent.futures,time,os,traceback
R=pathlib.Path('/root/agentodyssey-benchmark-20261018')
def record(kind,**kw):
 with (R/'setup_events.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),'kind':kind,**kw})+'\n')
 print(kind,kw,flush=True)
def download(urls,dest,sha):
 dest=pathlib.Path(dest)
 if dest.exists() and hashlib.file_digest(dest.open('rb'),'sha256').hexdigest()==sha:return
 for url in urls:
  try:
   record('download_start',url=url,path=str(dest))
   tmp=dest.with_suffix(dest.suffix+'.partial');n=0;last=time.monotonic();h=hashlib.sha256()
   with urllib.request.urlopen(url,timeout=45) as response,tmp.open('wb') as f:
    while True:
     b=response.read(4*1024*1024)
     if not b:break
     f.write(b);h.update(b);n+=len(b)
     if time.monotonic()-last>30:record('download_progress',path=str(dest),bytes=n);last=time.monotonic()
   assert h.hexdigest()==sha,(h.hexdigest(),sha)
   tmp.replace(dest);record('download_done',path=str(dest),bytes=n,sha256=sha);return
  except Exception as e:record('download_failed',url=url,error=repr(e))
 raise RuntimeError('All download sources failed for '+str(dest))
def runtime():
 dest=R/'llama.tar.gz'
 download(['https://github.com/ggml-org/llama.cpp/releases/download/b11719/llama-b11719-bin-ubuntu-x64.tar.gz'],dest,'2c50edd1422cdc686a1620923a7dda9a33634509566d2821155fb3d4879510a3')
 target=R/'runtime';target.mkdir(exist_ok=True)
 with tarfile.open(dest) as tar:
  for m in tar.getmembers():assert (target/m.name).resolve().is_relative_to(target.resolve())
  tar.extractall(target)
 record('runtime_ready',files=[str(p) for p in target.rglob('llama-server')])
def model():
 (R/'models').mkdir(exist_ok=True)
 suffix='unsloth/Qwen3.5-4B-GGUF/resolve/e87f176479d0855a907a41277aca2f8ee7a09523/Qwen3.5-4B-BF16.gguf'
 download(['https://hf-mirror.com/'+suffix,'https://huggingface.co/'+suffix],R/'models/Qwen3.5-4B-BF16.gguf','9e6e2841a75f503ccb330831832fd7861266e187e0dbf149a954219ccb8c197a')
def dependencies():
 subprocess.run(['python3','-m','venv',str(R/'.venv')],check=True)
 pip=[str(R/'.venv/bin/python'),'-m','pip']
 for args in [ ['install','--no-cache-dir','gymnasium','termcolor','psutil','openai','requests','numpy','cmake','ninja'], ['install','--no-cache-dir','torch','--index-url','https://download.pytorch.org/whl/cpu'] ]:
  p=subprocess.run(pip+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  (R/('pip_'+('torch' if 'torch' in args else 'base')+'.log')).write_text(p.stdout)
  record('pip_result',args=args,returncode=p.returncode,tail=p.stdout[-1500:])
  if p.returncode:raise RuntimeError('Dependency installation failed')
 subprocess.run(pip+['freeze'],stdout=(R/'requirements.lock.txt').open('w'),check=True)
def source():
 z=R/'agentodyssey-source.zip';target=R/'agentodyssey';target.mkdir(exist_ok=True)
 with zipfile.ZipFile(z) as archive:
  prefix=archive.namelist()[0].split('/')[0]+'/'
  for name in archive.namelist():
   rel=name[len(prefix):];out=target/rel
   assert out.resolve().is_relative_to(target.resolve())
   if not rel:continue
   if name.endswith('/'):out.mkdir(parents=True,exist_ok=True)
   else:out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(archive.read(name))
 record('source_ready',path=str(target))
if __name__=='__main__':
 source()
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  futures={pool.submit(fn):fn.__name__ for fn in [runtime,model,dependencies]}
  for f in concurrent.futures.as_completed(futures):
   try:f.result()
   except Exception as e:record('task_failed',task=futures[f],error=traceback.format_exc())
 record('bootstrap_finished')
