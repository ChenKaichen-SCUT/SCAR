import pathlib,subprocess,time,json,urllib.request,hashlib
R=pathlib.Path('/root/agentodyssey-benchmark-20261018')
while not (R/'base_ready.flag').exists():time.sleep(5)
pip=[str(R/'.venv/bin/python'),'-m','pip']
with (R/'pip_mem0.log').open('w') as f:subprocess.run(pip+['install','--no-cache-dir','--timeout','20','--retries','2','mem0ai==2.2.1','faiss-cpu','sentence-transformers','--index-url','https://mirrors.huaweicloud.com/repository/pypi/simple'],stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run(pip+['freeze'],stdout=(R/'requirements.lock.txt').open('w'),check=True)
(R/'mem0_installed.flag').write_text('ok')
