"""Zero-API native replay of every archived action; no decision policy imported."""
import argparse
import tempfile
from pathlib import Path
from scar.environment import AGENT_ID,state_digest
from .environment import create_initial
from .common import RESULTS,load,write,read_gzip,sha,ROOT,METHODS
from .evaluate import physical


def replay_one(task,method,root):
    folder=RESULTS/'runs'/f"{task['task_id']}__{method}"
    summary=load(folder/'summary.json');rows=read_gzip(folder/'trajectory.jsonl.gz')
    env,history=create_initial(task['game_name'],task['initial_seed'],root)
    assert state_digest(env)==task['initial_state_hash']
    target=env.world.auxiliary['obj_name_to_id'][task['target_item']]
    crafted0=env.curr_agents_state['objects_crafted'][AGENT_ID].get(target,0)
    assert len(rows)==summary['steps']<=100
    for step,row in enumerate(rows,1):
        assert row['step']==step
        assert env.obs[AGENT_ID]==row['observation']
        assert state_digest(env)==row['physical_before']['state_hash']
        obs,reward,done,info=env.step({AGENT_ID:row['action']});env.update_scores(reward)
        assert obs[AGENT_ID]==row['feedback']
        assert state_digest(env)==row['state_hash']
        actual=physical(env,target)
        success=actual['target_owned']>=1 and actual['crafted'].get(target,0)-crafted0>=1
        assert success==row['success']
        for fact in row['public_knowledge_after'].values():
            assert fact['observed_step']<=obs[AGENT_ID]['step']
        for event in row['knowledge_delta'].get('events',[]):assert event['observed_step']<=obs[AGENT_ID]['step']
    requests=read_gzip(folder/'requests.jsonl.gz')
    assert len({r['request_id'] for r in requests})==len(requests)
    assert all(1<=r['step']<=len(rows)+1 for r in requests)
    assert all(r['model']=='deepseek-flash' and r['temperature']==0.7 and r['thinking']=='disabled' for r in requests)
    if method=='A4':assert not requests
    return dict(task_id=task['task_id'],method=method,steps=len(rows),requests=len(requests),passed=True,
        final_hash=state_digest(env),true_success=rows[-1]['success'] if rows else False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--site',choices=['server','local'],required=True);parser.add_argument('--runtime',required=True);args=parser.parse_args()
    results=[];tasks=load(RESULTS/'tasks.json');root=Path(args.runtime);root.mkdir(parents=True,exist_ok=True)
    for task in tasks:
        for method in METHODS:
            with tempfile.TemporaryDirectory(dir=root) as directory:
                results.append(replay_one(task,method,Path(directory)))
    old=load(RESULTS/'prior_manifest.json')
    files=old.get('files',old)
    assert all(sha(ROOT/p)==h for p,h in files.items() if p!='base_commit')
    result=dict(passed=True,site=args.site,runs=results,trajectory_count=len(results),historical_files_unchanged=len(files),
        real_replay_actions=sum(r['steps'] for r in results),new_api_calls=0,
        native_replay_uses_uninstrumented_dispatch=True)
    write(RESULTS/f'replay_{args.site}.json',result)
    print('native replay passed',len(results))

if __name__=='__main__':main()
