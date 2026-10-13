"""One native step per actual SCAR override, from its exact pre-action state.

Does not run a controller, instantiate a provider, or continue alternate episodes.
Hidden evaluator graphs only label outcomes AFTER both actions have run.
"""
import argparse
import random
import tempfile
import numpy as np
from pathlib import Path
from .common import *
from scar.environment import AGENT_ID, snapshot, restore, state_digest
from scar_stage17.environment import create_initial
from scar_stage17.evaluate import physical
from scar_stage14.knowledge import Knowledge
from scar.agents.scar.state import feedback_text

def gains(before,after,graph):
    relevant=set(graph)
    for rule in graph.values():relevant.update(rule['ingredients'])
    return dict(health=after['health'],target_owned=after['target_owned'],
        production={k:after['crafted'].get(k,0)-before['crafted'].get(k,0) for k in graph if after['crafted'].get(k,0)>before['crafted'].get(k,0)},
        material_gains={k:after['possessed'].get(k,0)-before['possessed'].get(k,0) for k in relevant if after['possessed'].get(k,0)>before['possessed'].get(k,0)})

def run(site):
    deny_network();frozen=baseline();output=[]
    truth=load(RESULTS/'evaluator_truth.json')
    for t in load(RESULTS/'tasks.json'):
        graph=truth[t['task_id']]['recipes']
        rows=read_gzip(run_dir(t,'A0')/'trajectory.jsonl.gz')
        with tempfile.TemporaryDirectory(prefix='scar17-cf-') as tmp:
            env,_=create_initial(t['game_name'],t['initial_seed'],Path(tmp))
            assert state_digest(env)==t['initial_state_hash']
            target=truth[t['task_id']]['target_id']
            for r in rows:
                assert state_digest(env)==r['physical_before']['state_hash']
                d=r['decision']['decision'];proposal=d['proposed_action']
                changed=proposal!=r['action'];alternate=None
                if changed:
                    prng,nrng=random.getstate(),np.random.get_state()
                    clone=restore(snapshot(env))
                    assert state_digest(clone)==r['physical_before']['state_hash']
                    obs,rew,done,info=clone.step({AGENT_ID:proposal});clone.update_scores(rew)
                    after=physical(clone,target)
                    kb=Knowledge.from_dict(dict(facts=r['public_knowledge_before']))
                    delta=kb.observe(obs[AGENT_ID],proposal)
                    alternate=dict(action=proposal,feedback=obs[AGENT_ID],done=bool(done),physical_after=after,
                        death='I have died.' in obs[AGENT_ID]['text'],
                        knowledge_delta=delta,gains=gains(r['physical_before'],after,graph),state_hash=state_digest(clone))
                    random.setstate(prng);np.random.set_state(nrng)
                obs,rew,done,info=env.step({AGENT_ID:r['action']});env.update_scores(rew)
                assert state_digest(env)==r['state_hash'] and obs[AGENT_ID]==r['feedback']
                actual=gains(r['physical_before'],r['physical_after'],graph)
                labels=[];actual_advantages=[]
                if alternate:
                    cf=alternate['gains'];names={v['name'] for v in graph.values()}
                    actual_failure=bool(r['death'] or actual['health']<=0 or (r['done'] and not r['success']))
                    cf_failure=bool(alternate['death'] or cf['health']<=0 or alternate['done'])
                    an=set(r['knowledge_delta']['new_relations'])&names
                    cn=set(alternate['knowledge_delta']['new_relations'])&names
                    if not actual_failure and not cf_failure and cf['health']>actual['health']:labels.append('proposal_preserves_more_health')
                    if actual_failure and not cf_failure:labels.append('proposal_avoids_immediate_terminal_failure')
                    produced_before=r['target_produced_during_task']-r['metrics']['actual_production'].get(target,0)
                    if cf['target_owned']>actual['target_owned'] and cf['production'].get(target,0)+produced_before>0:labels.append('proposal_more_target_owned_after_craft')
                    if set(cf['production'])-set(actual['production']):labels.append('proposal_extra_closure_production')
                    if cn-an:labels.append('proposal_extra_closure_relation')
                    if set(cf['material_gains'])-set(actual['material_gains']):labels.append('proposal_extra_relevant_material_type')
                    if not actual_failure and cf_failure:actual_advantages.append('actual_avoids_immediate_terminal_failure')
                    if not actual_failure and not cf_failure and actual['health']>cf['health']:actual_advantages.append('actual_preserves_more_health')
                    if set(actual['production'])-set(cf['production']):actual_advantages.append('actual_extra_closure_production')
                    if an-cn:actual_advantages.append('actual_extra_closure_relation')
                    if set(actual['material_gains'])-set(cf['material_gains']):actual_advantages.append('actual_extra_relevant_material_type')
                    if actual['target_owned']>cf['target_owned'] and r['target_produced_during_task']>0:actual_advantages.append('actual_more_target_owned_after_craft')
                output.append(dict(evidence_id=eid(t,'A0',r['step']),task_id=t['task_id'],step=r['step'],
                    before_hash=r['physical_before']['state_hash'],actual_action=r['action'],proposal=proposal,
                    overridden=changed,actual_gains=actual,alternate=alternate,local_dimensions=labels,
                    actual_death=r['death'],
                    actual_advantages=actual_advantages,
                    interpretation='One-step dimension comparison only; tradeoffs and later episode success are not identified.'))
        print(t['task_id'],len(rows),'factual steps verified',flush=True)
    gzip_rows(OUT/f'counterfactual_{site}.jsonl.gz',output)
    write(OUT/f'counterfactual_{site}_receipt.json',dict(site=site,actual_actions=len(output),
        alternative_actions=sum(r['overridden'] for r in output),all_factual_hashes_match=True,
        new_api_calls=0,network_guard=True,unchanged_inputs=baseline(),
        output_sha256=sha(OUT/f'counterfactual_{site}.jsonl.gz')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--site',choices=['local','server'],default='local');run(p.parse_args().site)
