"""No-network end-to-end runner/memory smoke for all seven configurations."""
import argparse
import contextlib
import copy
import gzip
import json
from pathlib import Path
import tempfile
from scar.io import atomic_json
from scar_stage14.common import load
from scar_stage15.run import episode,make_tasks

class FixedProvider:
    def __init__(self,*args,**kwargs):pass
    def generate(self,*args,**kwargs):
        return {'response':json.dumps({'action':'inspect inventory','reasoning':'offline integration fixture'}),
                'num_input_tokens':0,'num_output_tokens':0}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    config=load('configs/protocol_stage15.json');case=load('results/stage11/cases.json')[0]
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        initial=Path(tmp)/'initial.pkl';initial.write_bytes(gzip.decompress(Path(f"results/stage11/initial_states/{case['id']}.pkl.gz").read_bytes()))
        for task in make_tasks(config,[case]):
            task.update(max_steps=1,initial_snapshot=str(initial))
            result=episode(task,config,tmp,'NO_KEY_OFFLINE',1,provider_factory=FixedProvider)
            assert result['status']=='completed',(task['algorithm'],result.get('error'))
            from scar_stage15.agent import make_agent
            agent=make_agent(task['algorithm'],task['game'],FixedProvider(),config,Path(tmp)/'restore')
            agent.load_memory(Path(tmp)/'runs'/task['task_id']/'steps'/'0001'/'memory')
            assert len(agent.short_term_memory)<=5
            rows.append({'method':task['algorithm'],'status':result['status'],'steps':result['steps'],'api_calls':result['api_calls'],'restored_memory':True})
    atomic_json(a.output,{'rows':rows,'api_calls':0});print('Seven runner and memory smoke tests passed; zero API.')

if __name__=='__main__':main()
