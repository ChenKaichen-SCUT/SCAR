"""Record official sources and installed dependencies without copying downloads."""
import importlib.metadata as metadata
import os
import subprocess
import sys
from pathlib import Path
from .common import write,RESULTS,sha,BASE_COMMIT


def main():
    engine=Path(os.environ['AGENTODYSSEY_ROOT']);ada=engine.parent/'AdaPlanner';sources={}
    for name,path in {'agentodyssey':engine,'AdaPlanner':ada}.items():
        paths=[path/'agents/fixed_size/short_term_memory_agent.py',path/'agents/long_context_agent.py',path/'agents/llm_agent_config.py'] if name=='agentodyssey' else [path/'ALFWorld/alfworld.ipynb',path/'ALFWorld/prompt.py',path/'README.md',path/'LICENSE']
        sources[name]=dict(url='https://github.com/'+('agentodyssey/agentodyssey' if name=='agentodyssey' else 'haotiansun14/AdaPlanner'),commit=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip(),license='Apache-2.0' if name=='agentodyssey' else 'MIT',files={str(p.relative_to(path)):sha(p) for p in paths})
    sources['SCAR']=dict(url='https://github.com/ChenKaichen-SCUT/SCAR',commit=BASE_COMMIT,license='No repository LICENSE file at frozen commit; unspecified',baseline='scar_stage16 S1_P1_P3')
    versions={}
    for name in ['openai','numpy','torch','cloudpickle','pydantic','pytest','pandas','scipy','matplotlib']:
        try:versions[name]=metadata.version(name)
        except metadata.PackageNotFoundError:versions[name]='not installed / not required'
    write(RESULTS/'sources.json',dict(sources=sources,python=sys.version,dependencies=versions,
        model_pricing_source='https://api-docs.deepseek.com/quick_start/pricing/',
        pricing_scope='conservative peak-rate protocol estimate, not account invoice'))

if __name__=='__main__':main()
