"""Native ONE-step counterfactuals on the server at SCAR18's saved states.

"Local" describes a causal time horizon, not this script's execution machine.
No new proposals, provider, full alternate episode, or policy revision.
"""
import argparse
import contextlib
import io
import random
import tempfile
from pathlib import Path
import numpy as np
from scar.environment import AGENT_ID, snapshot, restore, state_digest
from scar_stage17.environment import create_initial
from scar_stage17.evaluate import physical
from scar_stage14.knowledge import Knowledge
from .common import ROOT, RESULTS, load, write, read_gzip, gzip_rows, deny_network, sha


def difference(before,after):
    return dict(health=after['health'],target_owned=after['target_owned'],
        production={n:v-before['crafted'].get(n,0) for n,v in after['crafted'].items() if v>before['crafted'].get(n,0)},
        material_gains={n:v-before['possessed'].get(n,0) for n,v in after['possessed'].items() if v>before['possessed'].get(n,0)})


def main():
    deny_network();records=[];actual_count=0;alternate_count=0
    tasks=load(RESULTS/'tasks.json')
    for task in tasks:
        rows=read_gzip(RESULTS/'runs'/f"{task['task_id']}__SCAR18/trajectory.jsonl.gz")
        with tempfile.TemporaryDirectory(prefix='scar18-local-effect-') as temp:
            with contextlib.redirect_stdout(io.StringIO()):env,history=create_initial(task['game_name'],task['initial_seed'],Path(temp))
            assert state_digest(env)==task['initial_state_hash']
            target=env.world.auxiliary['obj_name_to_id'][task['target_item']]
            crafted0=env.curr_agents_state['objects_crafted'][AGENT_ID].get(target,0)
            for r in rows:
                assert state_digest(env)==r['physical_before']['state_hash']
                audit=r['decision']['decision']['stage18']
                alternatives={}
                for label,action in [('old_controller',audit.get('original_s1_candidate')),('raw_llm',audit['llm_proposal'])]:
                    if action and action!=r['action']:alternatives.setdefault(action,[]).append(label)
                for action,labels in alternatives.items():
                    py_rng,np_rng=random.getstate(),np.random.get_state()
                    clone=restore(snapshot(env));assert state_digest(clone)==r['physical_before']['state_hash']
                    obs,reward,done,info=clone.step({AGENT_ID:action});clone.update_scores(reward)
                    after=physical(clone,target);kb=Knowledge.from_dict(dict(facts=r['public_knowledge_before']))
                    delta=kb.observe(obs[AGENT_ID],action)
                    cf_success=after['target_owned']>=task['target_amount'] and after['crafted'].get(target,0)-crafted0>=task['target_amount']
                    cf_failed=bool(getattr(reward[AGENT_ID],'death',False) or after['health']<=0 or done) and not cf_success
                    actual_failed=bool(r['death'] or r['physical_after']['health']<=0 or r['done']) and not r['success']
                    a=difference(r['physical_before'],r['physical_after']);b=difference(r['physical_before'],after)
                    wins=[];losses=[]
                    if cf_failed and not actual_failed:wins.append('avoids_immediate_terminal_failure')
                    if actual_failed and not cf_failed:losses.append('avoids_immediate_terminal_failure')
                    # Native death may revive to HP100. A revived terminal
                    # state must never appear to win a survival/HP comparison.
                    if not actual_failed and not cf_failed:
                        if a['health']>b['health']:wins.append('higher_post_action_health')
                        if b['health']>a['health']:losses.append('higher_post_action_health')
                    for field in ('production','material_gains'):
                        if set(a[field])-set(b[field]):wins.append('extra_'+field+'_type')
                        if set(b[field])-set(a[field]):losses.append('extra_'+field+'_type')
                    if set(r['knowledge_delta']['new_relations'])-set(delta['new_relations']):wins.append('extra_public_recipe_relation')
                    if set(delta['new_relations'])-set(r['knowledge_delta']['new_relations']):losses.append('extra_public_recipe_relation')
                    if r['success'] and not cf_success:wins.append('immediate_target_completion')
                    if cf_success and not r['success']:losses.append('immediate_target_completion')
                    records.append(dict(evidence_id=f"{task['task_id']}__SCAR18:a{r['step']:03d}",task_id=task['task_id'],step=r['step'],
                        before_hash=r['physical_before']['state_hash'],actual_action=r['action'],alternate_action=action,
                        alternate_labels=labels,actual_gains=a,alternate_gains=b,actual_terminal_failure=actual_failed,
                        alternate_terminal_failure=cf_failed,actual_success=r['success'],alternate_success=cf_success,
                        actual_advantage_dimensions=wins,alternate_advantage_dimensions=losses,
                        alternate_feedback=obs[AGENT_ID],alternate_knowledge_delta=delta,
                        alternate_state_hash=state_digest(clone),scope='same physical/RNG state; one native action; dimension-specific, not an episode-level or module-isolated causal effect'))
                    alternate_count+=1;random.setstate(py_rng);np.random.set_state(np_rng)
                obs,reward,done,info=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback']
                actual_count+=1
        print(task['task_id'],'same-state branches and actual hashes verified',flush=True)
    gzip_rows(RESULTS/'same_state_effects_server.jsonl.gz',records)
    old=[r for r in records if 'old_controller' in r['alternate_labels']]
    llm=[r for r in records if 'raw_llm' in r['alternate_labels']]
    summarize=lambda rr:dict(n=len(rr),actual_advantage_dimensions={k:sum(k in r['actual_advantage_dimensions'] for r in rr) for k in sorted({k for r in rr for k in r['actual_advantage_dimensions']})},
        alternate_advantage_dimensions={k:sum(k in r['alternate_advantage_dimensions'] for r in rr) for k in sorted({k for r in rr for k in r['alternate_advantage_dimensions']})})
    write(RESULTS/'same_state_effects_receipt.json',dict(site='server',passed=True,new_api_calls=0,network_guard=True,
        replayed_actual_actions=actual_count,one_step_alternatives=alternate_count,
        old_candidate_comparisons=summarize(old),raw_llm_comparisons=summarize(llm),
        output_sha256=sha(RESULTS/'same_state_effects_server.jsonl.gz'),
        interpretation='Old candidate is a shadow at SCAR18 public/controller state, not a rerun of Stage17 episodes. All positive and negative dimensions retained.'))


if __name__=='__main__':main()
