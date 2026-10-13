"""Reconstruct all initial states and feasibility witnesses without any policy/API."""
import argparse
import tempfile
from pathlib import Path
from scar.environment import AGENT_ID,state_digest
from scar.io import digest
from scar_v3.hard import owned
from .environment import create_initial
from .common import RESULTS,load,write,read_gzip


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--site',required=True);parser.add_argument('--runtime',required=True);args=parser.parse_args()
    root=Path(args.runtime);root.mkdir(parents=True,exist_ok=True)
    witnesses={r['task_id']:r for r in read_gzip(RESULTS/'native_feasibility_witnesses.jsonl.gz')};checks=[]
    for task in load(RESULTS/'tasks.json'):
        with tempfile.TemporaryDirectory(dir=root) as directory:
            env,history=create_initial(task['game_name'],task['initial_seed'],directory)
            assert state_digest(env)==task['initial_state_hash'] and digest(history)==task['initial_public_history_hash']
            oid=env.world.auxiliary['obj_name_to_id'][task['target_item']];before=env.curr_agents_state['objects_crafted'][AGENT_ID].get(oid,0)
            assert owned(env,oid)==0
            trace=witnesses[task['task_id']]['trace']
            for row in trace:
                assert env.obs[AGENT_ID]==row['before']
                obs,reward,done,info=env.step({AGENT_ID:row['action']});env.update_scores(reward)
                assert not done and not reward[AGENT_ID].death
                assert obs[AGENT_ID]==row['after'] and state_digest(env)==row['state_hash']
            assert owned(env,oid)>=1 and env.curr_agents_state['objects_crafted'][AGENT_ID].get(oid,0)>before
            checks.append(dict(task_id=task['task_id'],passed=True,witness_steps=len(trace)))
    write(RESULTS/f'task_check_{args.site}.json',dict(passed=True,checks=checks,api_calls=0,formal_policy_runs=0))

if __name__=='__main__':main()
