"""Separate evaluator checks at the three original historical veto checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path

from scar.environment import AGENT_ID,restore
from scar_public.experiments.replay_real_reuse import execute
from scar_public.resource_trial import fresh,public_outcome


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint-root',type=Path,required=True)
    p.add_argument('--reuse-result',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    result=dict(api_calls=0,validation_environment_actions=0,checks=[])
    for case in json.loads(a.reuse_result.read_text())['vetoes']:
        n=case['proposal_step'];cp=a.checkpoint_root/f'{n-1:04d}'/'environment.pkl'
        out=a.output/str(n);out.mkdir();env=restore(cp,out)
        before=env.obs[AGENT_ID]['text'];scores=json.loads(json.dumps(env.scores))
        after,done=execute(env,case['action'])
        status=public_outcome(after,case['action'])
        result['checks'].append(dict(proposal_step=n,action=case['action'],
            checkpoint_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),
            observation=before,next_observation=after,status=status,
            same_public_physical_state=fresh(before)==fresh(after),same_scores=scores==env.scores))
        result['validation_environment_actions']+=1
        assert status=='failure' and fresh(before)==fresh(after) and scores==env.scores
    (a.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}))


if __name__=='__main__':main()
