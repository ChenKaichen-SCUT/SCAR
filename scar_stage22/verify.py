"""Independent zero-API native replay, score/usage audit and local contrasts."""
import argparse
import contextlib
import copy
import io
import json
import random
import socket
import sqlite3
import tempfile
from pathlib import Path
import numpy as np
from scar.environment import create_environment, snapshot, restore, state_digest
from scar.io import digest
from scar.providers.deepseek import estimate_cost
from .config import ROOT, RESULTS, ENGINE, METHODS, GAMES, SEED, AGENT_ID, MODEL
from .analyze import read, rows, write, gzwrite, public_goal


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def delta_summary(env, reward, obs, info):
    a=env.agents[0]
    return dict(reward=vars(reward[AGENT_ID]),scores=copy.deepcopy(env.scores[AGENT_ID]),
                hp=a.hp,invalid=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False)),
                area=env.curr_agents_state['area'][AGENT_ID],
                tutorial_stage=env.curr_agents_state.get('tutorial_stage',{}).get(AGENT_ID),
                tutorial_passed=env.curr_agents_state.get('tutorial_passed',{}).get(AGENT_ID),
                public_goal=public_goal(obs[AGENT_ID]['text']),feedback=obs[AGENT_ID],
                main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress',{}).get(AGENT_ID)))


def replay_one(game,method):
    directory=RESULTS/'runs'/f'{game}__{method}'
    trajectory=rows(directory/'trajectory.jsonl.gz');initial=read(directory/'initial_public.json')
    comparisons=[];verified_actions=0;first_mismatch=None
    with tempfile.TemporaryDirectory(prefix='scar22-native-') as temp:
        random.seed(SEED); np.random.seed(SEED)
        # Official bootstrap uses unordered sets to break area-distance ties.
        # Restore only its originally sampled, immutable scenario parameters
        # from the native saved config. Keep its original RNG consumption and
        # all native transitions. This is an offline state reconstruction, not
        # a policy input and not a change to any formal experiment.
        import importlib
        cls=importlib.import_module(f'games.generated.{game}.rules.step_rules.main_quest').MainQuestStepRule
        original_bootstrap=cls._bootstrap
        recorded_generated=read(directory/'config.json')['world']['auxiliary'].get('main_quest',{}).get('generated',{})
        restored_parameters=[]
        def restore_bootstrap(self,env,world):
            original_bootstrap(self,env,world)
            for key in self._generated:
                if key in recorded_generated and self._generated[key]!=recorded_generated[key]:
                    restored_parameters.append(key)
                    self._generated[key]=copy.deepcopy(recorded_generated[key])
        cls._bootstrap=restore_bootstrap
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                env,obs=create_environment(game,SEED,Path(temp),upstream=ENGINE)
        finally:cls._bootstrap=original_bootstrap
        # Upstream stores list(set(...)) recipe presentation order. Restore the
        # saved run-specific order, not an order invented by this new process.
        import gzip
        with gzip.open(directory/'native_prebootstrap_config.json.gz','rt') as stream:
            native_initial=json.load(stream)
        env.world.auxiliary['ing_to_obj_map']=copy.deepcopy(native_initial['world']['auxiliary']['ing_to_obj_map'])
        assert obs[AGENT_ID]==initial['observation'] and state_digest(env)==initial['initial_state_hash']
        for r in trajectory:
            assert state_digest(env)==r['state_hash_before']
            alternate=None;proposal=r.get('decision',{}).get('proposed_action') if r.get('decision') else None
            if proposal and proposal!=r['action']:
                py_rng,np_rng=random.getstate(),np.random.get_state()
                clone=restore(snapshot(env))
                with contextlib.redirect_stdout(io.StringIO()):
                    o,w,d,i=clone.step({AGENT_ID:proposal});clone.update_scores(w)
                alternate=delta_summary(clone,w,o,i);alternate['done']=bool(d)
                random.setstate(py_rng);np.random.set_state(np_rng)
            with contextlib.redirect_stdout(io.StringIO()):
                o,w,d,i=env.step({AGENT_ID:r['action']});env.update_scores(w)
            checks=dict(feedback=o[AGENT_ID]==r['feedback'],reward=vars(w[AGENT_ID])==r['reward'],
                        state=state_digest(env)==r['state_hash'],done=bool(d)==r['done'])
            if not all(checks.values()):
                first_mismatch=dict(step=r['step'],checks=checks,
                     explanation='Replay stopped at first mismatch. No downstream same-state contrast is claimed; official dynamic set-order generation is not fully reproducible from seed alone.')
                break
            verified_actions=r['step']
            if alternate:
                actual=delta_summary(env,w,o,i);actual['done']=bool(d)
                positive=[];negative=[]
                for key in ('quest','side_quest','exploration','craft','unique_kill'):
                    av=actual['reward'].get(key,0);bv=alternate['reward'].get(key,0)
                    if av>bv:positive.append(key)
                    if bv>av:negative.append(key)
                if actual['invalid']<alternate['invalid']:positive.append('avoids_native_invalid')
                if alternate['invalid']<actual['invalid']:negative.append('avoids_native_invalid')
                if actual['tutorial_stage'] is not None and alternate['tutorial_stage'] is not None:
                    if actual['tutorial_stage']>alternate['tutorial_stage']:positive.append('tutorial_stage')
                    if alternate['tutorial_stage']>actual['tutorial_stage']:negative.append('tutorial_stage')
                comparisons.append(dict(evidence_id=f'{game}__{method}:a{r["step"]:03d}',game=game,step=r['step'],
                    before_hash=r['state_hash_before'],executed=r['action'],proposal=proposal,
                    actual=actual,alternate=alternate,actual_advantage_dimensions=positive,
                    proposal_advantage_dimensions=negative,
                    scope='one native action at identical physical and RNG state; no future policy rollout or total mechanism effect'))
    return dict(game=game,method=method,passed=first_mismatch is None,actions=len(trajectory),
                verified_actions=verified_actions,first_mismatch=first_mismatch,local_alternatives=len(comparisons),
                restored_recorded_bootstrap_parameters=restored_parameters),comparisons


def reconstruct_policy(game):
    from .integration import make_agent
    directory=RESULTS/'runs'/f'{game}__Stage18-Fixed'
    trajectory=rows(directory/'trajectory.jsonl.gz');requests=rows(directory/'requests.jsonl.gz')
    by_step={q['step']:q for q in requests if q['status']=='ok' and q['phase']=='action'}
    class SavedResponse:
        step=0
        def generate(self,user_prompt,system_prompt=None,**kwargs):
            q=by_step[self.step]
            messages=[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)]
            assert messages==q['messages'], (game,self.step,'model context')
            return dict(response=q['raw_response']['choices'][0]['message']['content'],
                        num_input_tokens=q['usage']['prompt_tokens'],num_output_tokens=q['usage']['completion_tokens'])
    with tempfile.TemporaryDirectory(prefix='scar22-policy-') as temp:
        provider=SavedResponse()
        with contextlib.redirect_stdout(io.StringIO()):
            agent=make_agent('Stage18-Fixed',game,provider,Path(temp)/'memory')
        agent.initialize_official(read(directory/'initial_public.json')['observation'])
        for r in trajectory:
            provider.step=r['step']
            action,*_=agent.act(r['observation'])
            assert action==r['action'], (game,r['step'],'policy action')
            assert digest(agent.decision)==digest(r['decision']), (game,r['step'],'policy state')
            agent.observe_transition(r['observation'],action,r['feedback'])
    return dict(game=game,actions=len(trajectory),model_contexts_and_decisions_exact=True)


def cached_replay(entry):
    game,method=entry
    directory=RESULTS/'runs'/f'{game}__{method}'
    cache=RESULTS/'replay_receipts';cache.mkdir(exist_ok=True)
    receipt=cache/f'{game}__{method}.json';cfpath=cache/f'{game}__{method}.contrasts.jsonl.gz'
    inputs={name:sha(directory/name) for name in ('trajectory.jsonl.gz','config.json','native_prebootstrap_config.json.gz')}
    if receipt.exists():
        saved=read(receipt)
        assert saved['inputs']==inputs, 'Replay inputs changed after verification'
        assert sha(cfpath)==saved['contrasts_sha256']
        return saved['replay'],rows(cfpath)
    result,cf=replay_one(game,method)
    gzwrite(cfpath,cf)
    write(receipt,dict(replay=result,inputs=inputs,contrasts_sha256=sha(cfpath),
                      verification_source_sha256=sha(Path(__file__)),api_calls=0))
    return result,cf


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime');args=parser.parse_args()
    def deny(*args,**kwargs):raise RuntimeError('Network prohibited in offline verification')
    socket.create_connection=socket.socket.connect=socket.socket.connect_ex=deny
    freeze=read(RESULTS/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in freeze['files'].items())
    assert all(sha(ENGINE/p)==h for p,h in freeze['engine_files'].items())
    prior=read(RESULTS/'prior_manifest.json')['files']
    assert all(sha(ROOT/p)==h for p,h in prior.items())
    records=[];requests=[];initials={};replays=[];comparisons=[];policy=[]
    for game in GAMES:
        for method in METHODS:
            folder=RESULTS/'runs'/f'{game}__{method}'
            t=rows(folder/'trajectory.jsonl.gz');q=rows(folder/'requests.jsonl.gz');s=read(folder/'summary.json');cfg=read(folder/'config.json')
            assert len(t)==s['steps']<=300 and cfg['step']==len(t)
            assert [r['step'] for r in t]==list(range(1,len(t)+1))
            assert s['status'] in ('step_limit','native_done'), s.get('error')
            assert s['status']!='step_limit' or len(t)==300
            assert cfg['scores'][AGENT_ID]==s['scores']==t[-1]['scores']
            accumulated={}
            for r in t:
                for k,v in r['reward'].items():accumulated[k]=accumulated.get(k,0)+v
                assert accumulated==r['scores']
            assert accumulated==cfg['scores'][AGENT_ID]
            initial=read(folder/'initial_public.json');initials.setdefault(game,[]).append(initial)
            assert initial['previous_history']==[]
            for r in q:
                assert r['start']>=__import__('datetime').datetime.fromisoformat(freeze['created_utc']).timestamp()
                for key in ('model','temperature','top_p','presence_penalty','thinking','max_tokens'):assert r[key]==MODEL[key]
                if r.get('usage'):
                    assert abs(estimate_cost(r['usage'],r['unit_prices'])-r['cost_usd'])<1e-12
            requests+=q;records.append(s)
            replay,cf=cached_replay((game,method));replays.append(replay);comparisons+=cf
            print(game,method,'native replay',replay,flush=True)
        assert len({digest(i['observation']) for i in initials[game]})==1, 'Initial public observations differ'
        policy.append(reconstruct_policy(game))
        print(game,'Stage18 saved-context and controller reconstruction passed',flush=True)
    assert len({q['request_id'] for q in requests})==len(requests)
    if args.runtime:
        with sqlite3.connect(Path(args.runtime)/'budget.sqlite') as db:
            ledger=[dict(zip(('request_id','reserved_usd','charged_usd','status'),r)) for r in db.execute('SELECT id,reserved,charged,status FROM requests ORDER BY id')]
    else:
        ledger=read(RESULTS/'cost_ledger.json')['requests']
    assert {r['request_id'] for r in ledger}=={r['request_id'] for r in requests}
    audit={q['request_id']:q for q in requests}
    for r in ledger:assert r['charged_usd']==audit[r['request_id']]['charged_or_reserved_usd']
    write(RESULTS/'cost_ledger.json',dict(requests=ledger,committed_usd=sum(r['charged_usd'] for r in ledger)))
    gzwrite(RESULTS/'same_state_local_contrasts.jsonl.gz',comparisons)
    write(RESULTS/'verification.json',dict(passed=True,passed_scope='Frozen source, raw record, score and usage integrity; native replay completeness is reported separately',runs=15,actions=sum(r['steps'] for r in records),
          requests=len(requests),cost_usd=sum(q.get('cost_usd',0) for q in requests),
          frozen_files_unchanged=len(freeze['files']),engine_files_unchanged=len(freeze['engine_files']),
          historical_files_unchanged=len(prior),native_replays=replays,policy_reconstruction=policy,
          local_alternatives=len(comparisons),api_calls=0,network_denied=True,
          same_initial_observation_per_game=True,
          native_replay_all_passed=all(r['passed'] for r in replays),
          initial_state_caveat='Pre-bootstrap recipe display orders differ; metropolis bootstrap scenario locations also differ. Dynamic side quest generation can diverge in offline replay. See initial_state_comparison.json and generated_scenario_comparison.json.',
          completed_failures_rerun=0))


if __name__=='__main__':main()
