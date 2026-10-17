"""No-API negative controls: replay untriggered games exactly with repair on."""
import argparse
import contextlib
import json
from pathlib import Path
import sys
from scar.environment import restore
from scar.io import atomic_json
from scar_public.continuation import ContinuationAgent
from scar_public.experiments.continuation_branch import ReusingProvider
from scar_public.experiments.core_trial import build_system


def main():
    p=argparse.ArgumentParser();p.add_argument('--block',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    provider=ReusingProvider(a.output.parent/(a.block.name+'_cache_audit'),'UNUSED',historical=a.block/'api')
    provider.cache_only=True;provider.arm='negative_control'
    agent=ContinuationAgent(provider,build_system(restore(a.block/'initial.pkl'),provider.model),'repair')
    count=0
    for path in sorted((a.block/'checked/trace').glob('*.json')):
        row=json.loads(path.read_text());provider.step=row['step']-1
        with contextlib.redirect_stdout(sys.stderr):
            action,_,_,raw=agent.act(dict(text=row['observation'],step=provider.step))
        parsed=json.loads(raw)
        assert action==row['action'], ('action',row['step'])
        assert not parsed['continuation']['trigger'], ('unexpected trigger',row['step'])
        assert parsed.get('frame')==json.loads(row['response']).get('frame'), ('frame',row['step'])
        if row['step']%25==0:
            checkpoint=a.block/'checked/checkpoints'/f"{row['step']:04d}"/'agent.json'
            actual=json.loads(json.dumps(agent.notebook.state()))
            expected=json.loads(checkpoint.read_text())
            if actual!=expected:
                delta={k:dict(actual=actual.get(k),expected=expected.get(k))
                       for k in set(actual)|set(expected) if actual.get(k)!=expected.get(k)}
                atomic_json(a.output.with_suffix('.mismatch.json'),delta)
                raise AssertionError(('memory',row['step'],list(delta)))
        count+=1
    result=dict(block=a.block.name,decisions=count,identical_actions=count,identical_frames=count,
                exact_cached_prompts=True,checkpoint_memory_equal=True,new_api_calls=0)
    atomic_json(a.output,result);print(json.dumps(result))


if __name__=='__main__':main()
