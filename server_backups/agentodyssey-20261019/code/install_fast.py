import pathlib,subprocess
R=pathlib.Path('/root/agentodyssey-benchmark-20261018')
pip=[str(R/'.venv/bin/python'),'-m','pip']
stages=[('base',['gymnasium','termcolor','psutil','openai','requests','numpy','--index-url','https://mirrors.huaweicloud.com/repository/pypi/simple']),('torch',['torch==2.10.0+cpu','--index-url','https://download.pytorch.org/whl/cpu','--extra-index-url','https://mirrors.huaweicloud.com/repository/pypi/simple'])]
for name,args in stages:
 with (R/('pip_'+name+'.log')).open('w') as f:
  p=subprocess.run(pip+['install','--no-cache-dir','--timeout','20','--retries','2']+args,stdout=f,stderr=subprocess.STDOUT)
 assert p.returncode==0,(name,p.returncode)
(R/'base_ready.flag').write_text('ok')
