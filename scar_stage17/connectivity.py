"""Very small real-API acceptance on an old goal, excluded from formal results."""
import copy
import json
from pathlib import Path
import argparse
from scar.environment import snapshot,restore,AGENT_ID,state_digest
from .common import RESULTS,write,gzip_rows
from .environment import create_initial
from .methods import make_method
from .provider import SharedDeepSeekProvider,CONFIG


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',required=True);parser.add_argument('--key-path',default='/root/.scar-deepseek-key');args=parser.parse_args()
    root=Path(args.runtime);root.mkdir(parents=True,exist_ok=True)
    if (RESULTS/'connectivity.json').exists():raise FileExistsError('Do not repeat paid connectivity checks')
    env,history=create_initial('robot_kingdom',171905,root/'initial');initial=snapshot(env);results=[];requests=[]
    for method in ('A1','A3'):
        provider=SharedDeepSeekProvider(root/method,root/'budget.sqlite',args.key_path)
        agent=make_method(method,'robot_kingdom',provider,'Craft and obtain 1 bandage_roll within 100 actions.','bandage_roll',history,root/method)
        test=restore(initial,root/method,agent=agent);provider.begin_step(1)
        before=copy.deepcopy(test.obs[AGENT_ID]);action,*_=agent.act(before)
        obs,reward,done,info=test.step({AGENT_ID:action});test.update_scores(reward)
        if hasattr(agent,'observe_transition'):agent.observe_transition(before,action,obs[AGENT_ID])
        rows=[json.loads(s) for s in provider.audit.read_text().splitlines()];requests.extend(dict(r,method=method) for r in rows)
        results.append(dict(method=method,action=action,before=before,after=obs[AGENT_ID],state_hash=state_digest(test),calls=len(rows)))
    gzip_rows(RESULTS/'connectivity_requests.jsonl.gz',requests)
    write(RESULTS/'connectivity.json',dict(passed=True,old_goal='bandage_roll',physical_seed=171905,formal=False,
        runs=results,api_calls=len(requests),cost_usd=sum(r['charged_or_reserved_usd'] for r in requests),
        config=CONFIG))
    print('connectivity successful',len(requests),'requests')

if __name__=='__main__':main()
