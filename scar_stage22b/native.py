"""Exact native prefixes and preregistered public-only reachability witnesses."""
import argparse
import contextlib
import copy
import importlib
import io
import math
import random
import tempfile
import numpy as np
from .common import *


def frame(env):
    # Some upstream serializers expose live auxiliary dictionaries. Detach the
    # entire frame so later native steps cannot rewrite earlier audit evidence.
    return copy.deepcopy(dict(world=env.world.to_dict(),agents=[a.to_dict() for a in env.agents],
                state=env.curr_agents_state,scores=env.scores,steps=env.steps))

def differences(before,after,path=''):
    if type(before)!=type(after):return [dict(path=path,before=before,after=after)]
    if isinstance(before,dict):
        result=[]
        for k in sorted(before.keys()|after.keys()):
            result+=differences(before.get(k),after.get(k),path+'/'+str(k))
        return result
    return [] if before==after else [dict(path=path,before=before,after=after)]

def create_actual(method,tmp):
    from scar.environment import create_environment,state_digest
    random.seed(42);np.random.seed(42)
    d=source(method);config=read(d/'config.json')
    cls=importlib.import_module('games.generated.mark.rules.step_rules.main_quest').MainQuestStepRule
    original=cls._bootstrap
    generated=config['world']['auxiliary']['main_quest']['generated']
    def recorded(self,env,world):
        original(self,env,world)
        for k in self._generated:
            if k in generated:self._generated[k]=copy.deepcopy(generated[k])
    cls._bootstrap=recorded
    try:
        with contextlib.redirect_stdout(io.StringIO()):env,obs=create_environment('mark',42,Path(tmp),upstream=ENGINE)
    finally:cls._bootstrap=original
    native=json.loads(gzip.decompress((d/'native_prebootstrap_config.json.gz').read_bytes()))
    env.world.auxiliary['ing_to_obj_map']=copy.deepcopy(native['world']['auxiliary']['ing_to_obj_map'])
    initial=read(d/'initial_public.json')
    assert obs[AGENT]==initial['observation'] and state_digest(env)==initial['initial_state_hash'],(method,'initial')
    return env


def witness(env,step,prior_text):
    """Human-authored diagnostic path, no hidden config read for action choice."""
    from scar.environment import snapshot,restore,state_digest
    from scar_v3.state import PublicState
    from scar_sequence.planner import q
    start_hash=state_digest(env);branch=restore(snapshot(env));assert state_digest(branch)==start_hash
    prior_quest=branch.scores[AGENT].get('quest',0);out=[]
    initial_observation=copy.deepcopy(branch.obs[AGENT]);remaining=301-step
    def public():return PublicState.observe(branch.obs[AGENT])
    def act(action,basis):
        assert len(out)<20
        before=copy.deepcopy(branch.obs[AGENT]);before_hash=state_digest(branch)
        with contextlib.redirect_stdout(io.StringIO()):
            obs,reward,done,info=branch.step({AGENT:action});branch.update_scores(reward)
        out.append(dict(index=len(out)+1,native_step=branch.steps,action=action,public_basis=basis,
            observation=before,feedback=obs[AGENT],reward=vars(reward[AGENT]),scores=copy.deepcopy(branch.scores[AGENT]),
            before_hash=before_hash,after_hash=state_digest(branch),done=bool(done)))
    goal_evidence='Craft an oak rod.' in prior_text
    if not goal_evidence:
        act('talk to remy','Original LLM proposal at this decision point; NPC publicly present and publicly offers a task reminder')
        goal_evidence='Craft an oak rod.' in branch.obs[AGENT]['text']
    stop=None
    if not goal_evidence:stop='First-stage objective not disclosed; no hidden objective substituted'
    else:
        # The observed hands and already seen two rooms are the only action
        # parameters. This scripted continuation is not a patched controller.
        for item,count in (public().hands or {}).copy().items():
            for _ in range(math.ceil(count)):
                act('drop '+q(item),'Free publicly occupied hands for the publicly requested material; dropped objects remain in this known room')
        if not (public().location or '').endswith(', library'):
            if 'library' not in (public().neighbors or []):stop='No publicly known adjacent path to material room'
            else:act('enter library','Previously visited library visibly contains oak_log')
        if not stop:
            if (public().ground or {}).get('oak_log',0)<=0:stop='No publicly visible oak_log in branch state'
            else:act('pick up oak_log','Public NPC task requires oak_log; it is visibly on the ground')
        if not stop:
            if not (public().hands or {}).get('oak_log',0):stop='Material acquisition failed'
            else:
                act('enter hall','The prior public hall observation contains workbench; library neighbors include hall')
                act('craft 1 oak_rod','Already disclosed NPC objective and native acquisition recipe, with the observed workbench in hall')
                if not (public().ground or {}).get('oak_rod',0):stop='Native craft did not expose the requested product'
                else:act('pick up oak_rod','Craft feedback puts the requested target on the ground; collect it to hold it')
    gained=branch.scores[AGENT].get('quest',0)>prior_quest
    return dict(start_before_action=step,actual_before_hash=start_hash,clone_initial_hash=start_hash,
        initial_observation=initial_observation,original_remaining_actions=remaining,branch_actions=len(out),
        first_stage_reward_gained=gained,new_quest_reward=branch.scores[AGENT].get('quest',0)-prior_quest,
        within_original_budget=len(out)<=remaining,stop_reason=stop,actions=out,
        full_main_quest_complete=bool(branch.curr_agents_state.get('main_quest_progress',{}).get(AGENT,{}).get('complete')),
        scope='Human public-information first-stage witness only; not patched-agent A/B, no resampled LLM and no claim of full quest recovery')


def execute(method):
    forbid_network();check_freeze()
    from scar.environment import state_digest
    from scar.io import digest
    trajectory=rows(source(method)/'trajectory.jsonl.gz');audit=[];branches=[];failure=None
    selected=read(RESULTS/'protocol.json')['manual_witness_steps']
    with tempfile.TemporaryDirectory(prefix='scar22b-native-') as tmp:
        env=create_actual(method,tmp);initial=frame(env);prior_text=env.obs[AGENT]['text']
        for r in trajectory:
            assert state_digest(env)==r['state_hash_before']
            before=frame(env)
            if method=='Stage18-Fixed' and r['step'] in selected:
                py_state,np_state=random.getstate(),np.random.get_state()
                branches.append(witness(env,r['step'],prior_text))
                random.setstate(py_state);np.random.set_state(np_state)
                assert state_digest(env)==r['state_hash_before'],'Offline branch mutated parent'
            with contextlib.redirect_stdout(io.StringIO()):
                obs,reward,done,info=env.step({AGENT:r['action']});env.update_scores(reward)
            checks=dict(feedback=obs[AGENT]==r['feedback'],reward=vars(reward[AGENT])==r['reward'],
                        state=state_digest(env)==r['state_hash'],done=bool(done)==r['done'])
            if not all(checks.values()):
                failure=dict(step=r['step'],checks=checks,scope='Stop at first mismatch; never report subsequent reconstructed hidden state as actual')
                break
            after=frame(env)
            audit.append(dict(method=method,step=r['step'],before_hash=r['state_hash_before'],after_hash=r['state_hash'],
                world_delta=differences(before,after),physical_after=after,stored_frame_digest=digest(after)))
            prior_text+='\n'+r['feedback']['text']
    assert all(digest(row['physical_after'])==row['stored_frame_digest'] for row in audit)
    write(RESULTS/'native'/f'{method}.initial.json',initial)
    gzwrite(RESULTS/'native'/f'{method}.jsonl.gz',audit)
    receipt=dict(method=method,verified_actions=len(audit),full_native_replay=len(audit)==300,
                 first_mismatch=failure,api_calls=0,network_denied=True,
                 immutable_frames_verified=True,source_sha256=sha(Path(__file__)))
    write(RESULTS/'native'/f'{method}.receipt.json',receipt)
    if method=='Stage18-Fixed':
        gzwrite(RESULTS/'public_recovery_witnesses.jsonl.gz',branches)
        write(RESULTS/'public_recovery_witnesses_summary.json',[{k:v for k,v in b.items() if k not in ('actions','initial_observation')} for b in branches])
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--method',choices=METHODS,required=True);execute(p.parse_args().method)
