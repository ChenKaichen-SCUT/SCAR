"""Read-only public-history replay of the frozen old policy; never calls an API.

Reconstructs the identical old prompts/actions and asks the new pure candidate
generator about those states. This measures changed eligibility, NOT new scores.
"""
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from scar.io import atomic_json
from scar_public.provider import Provider
from scar_public.continuation import task_key
from scar_public.obstacle_repair import repair_programs, route_rejections


class ReplayProvider(Provider):
    def __init__(self, output, directories):
        super().__init__(output,'UNUSED');self.directories=directories;self.reused=0

    def request(self,messages,repair=0,options=None):
        payload=dict(model=self.model,messages=messages,temperature=.7,top_p=.8,
            presence_penalty=0,max_tokens=1536,thinking={'type':'disabled'},response_format={'type':'json_object'})
        if options:payload.update(options)
        h=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        for directory in self.directories:
            path=directory/f'{self.step:04d}-{repair}-{h[:16]}.response.json'
            if path.exists():
                self.reused+=1
                return json.loads(path.read_text())
        raise RuntimeError(f'No historical request at {self.step}/{repair}/{h}; no API fallback')


def main():
    p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True)
    p.add_argument('--block',type=Path,required=True);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    spec=importlib.util.spec_from_file_location('frozen_old_obstacle',a.source)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    records=[]

    class AuditAgent(old.ObstacleRepairAgent):
        def finalize_decision(self,executed,obs,step,prompt,query):
            original=copy.deepcopy(executed);attempts=copy.deepcopy(self.obstacle_attempts)
            access=copy.deepcopy(self.access_methods);task=task_key(self.notebook)
            result=super().finalize_decision(executed,obs,step,prompt,query)
            event=result['continuation']
            if 'programs' not in event:return result
            goals=list(dict.fromkeys(r['quote'] for r in self.notebook.progress_tasks.values()))
            quote=original.get('frame',{}).get('goal_quote','')
            if len(quote)>=12 and any(quote in t for t in self.notebook.observations):goals=list(dict.fromkeys([quote]+goals))
            audit=[];new=repair_programs(self.notebook,original,goals,self.continuation,task,attempts,access,audit)
            contract=event.get('contract');old_route=[]
            if contract:
                support=contract.get('support',{})
                if isinstance(support,dict):old_route=support.get('observed_route',support.get('route',[]))
            records.append(dict(step=step+1,old_action=result['action'],old_changed=event['changed'],
                original=original['action'],old_contract=contract,old_programs=event['programs'],
                new_programs=new,rejections=audit,
                old_selected_route_blockers=route_rejections(self.notebook.model,old_route,self.continuation,task),
                selected_still_eligible=bool(contract) and any(c['action']==contract['action'] and c['target']==contract['target'] for c in new)))
            return result

    # The frozen system string is stored in a public request (no credentials).
    import gzip
    request=next((a.block/'api').glob('0000-0-*.request.json.gz'))
    system=json.loads(gzip.decompress(request.read_bytes()))['messages'][0]['content']
    # build_system supplies the base; agent construction adds the shared suffix.
    from scar_public.evidence import EVIDENCE_INSTRUCTION
    system=system.split(EVIDENCE_INSTRUCTION)[0]
    provider=ReplayProvider(a.output/'cache_audit',[a.old/'api',a.block/'api'])
    agent=AuditAgent(provider,system)
    count=0
    for path in sorted((a.old/'trace').glob('*.json')):
        row=json.loads(path.read_text());provider.step=row['step']-1
        with contextlib.redirect_stdout(sys.stderr):action,*_=agent.act(dict(text=row['observation'],step=provider.step))
        assert action==row['action'],(path.name,action,row['action'])
        count+=1
    atomic_json(a.output/'audit.json',dict(old=str(a.old),old_source=str(a.source),steps=count,
        cached_requests=provider.reused,new_api_requests=0,records=records,
        qualification='Identical old public histories; candidate eligibility only, no counterfactual game-score inference'))
    print(json.dumps(dict(steps=count,records=len(records),cached_requests=provider.reused,new_api_requests=0)))


if __name__=='__main__':main()
