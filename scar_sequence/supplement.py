"""Official lock-release and task-switch probes; no invented feedback."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import shlex
from scar.io import atomic_json,digest
from scar.environment import AGENT_ID,snapshot,restore,state_digest
from scar.diagnostics.build import transition
from scar_sequence.build import GAMES,controlled_world,static_environment
from scar_sequence.public import ResourceTable


def goal_reached(env,goal):
    if goal['kind']=='tutorial':
        return env.curr_agents_state.get('tutorial_stage',{}).get(AGENT_ID,0)>=goal['stage']
    from scar_v3.hard import goal_reached as original
    return original(env,goal)


def build(output):
    root=Path(output);cases=json.loads((root/'cases.json').read_text())
    if any(c['kind']!='craft' for c in cases):return
    for gi,game in enumerate(GAMES):
        for kind in ['lock_release','goal_switch']:
            if game=='robot_kingdom' and kind=='goal_switch':
                continue  # Official default disables tutorial; do not fabricate task changes.
            folder=root/'supplement_v2'/f'{game}-{kind}';folder.mkdir(parents=True,exist_ok=True)
            seed=56000+gi*10+(kind=='goal_switch');history=[]
            if kind=='lock_release':
                env,areas,source_hash=controlled_world(game,seed,folder/'world')
                key=env.world.objects['obj_key'].name
                areas[0].objects['obj_key']=1;areas[1].objects['obj_key']=1
                for left,right in zip(areas,areas[1:]):
                    left.neighbors[right.id].locked=True;right.neighbors[left.id].locked=True
                transition(env,'wait')
                for action in ['enter '+areas[1].name,'pick up '+key,'enter '+areas[1].name,'enter '+areas[0].name]:
                    r=transition(env,action);history.append({k:r[k] for k in ['before','action','after']})
                goal={'kind':'location','area_id':areas[2].id,'name':areas[2].name}
                target='enter '+areas[2].name
                witness=['enter '+areas[1].name,'pick up '+key,'enter '+areas[2].name]
                public_goal=f'Reach {areas[2].name}. Follow the observed map; some doors may need unlocking. Previously unlocked doors may be traversed again.'
                # Reveal the second neighboring destination by the real history
                # of visiting area 1; no route is supplied in the objective.
                knowledge='demonstrated_rules'
                initialization={'edits':['disable optional online expansion','three original areas linked','clear NPCs and enable visibility',
                        'two locked official edges and two existing keys'],'source_world_hash':source_hash,'areas':[a.id for a in areas]}
            else:
                env,_=static_environment(game,seed,folder/'world')
                r=transition(env,'inspect inventory')
                history=[{k:r[k] for k in ['before','action','after']}]
                table=ResourceTable().observe(env.obs[AGENT_ID]);target=table.state['public_goal']
                goal={'kind':'tutorial','stage':10,'name':'complete first ten official tutorial stages'}
                public_goal='Follow the current publicly announced task. Complete the first ten tutorial steps; update your task when the game announces the next Required action.'
                knowledge='interaction_discovery'
                initialization={'edits':['disable optional online expansion'],'source':'official_reset_and_failed_inspect_inventory'}
                trial=restore(snapshot(env));witness=[]
                for _ in range(16):
                    if goal_reached(trial,goal):break
                    action=ResourceTable().observe(trial.obs[AGENT_ID]).state['public_goal']
                    if not action:raise ValueError('Missing official public task')
                    witness.append(action);transition(trial,action)
            start=snapshot(env);checks=[]
            for _ in range(2):
                trial=restore(start);trace=[]
                for action in witness:
                    r=transition(trial,action);trace.append(dict(r,state_hash=state_digest(trial)))
                if not goal_reached(trial,goal):raise ValueError('Official probe witness failed')
                checks.append({'final_hash':state_digest(trial),'trace':trace})
            assert checks[0]['final_hash']==checks[1]['final_hash']
            (folder/'initial.pkl').write_bytes(start)
            family=digest([game,kind,initialization.get('areas','official_first10')])
            cases.append({'id':'sequence-'+family[:16],'family':family,'game':game,'seed':seed,'kind':kind,
                'source_cluster':game,'mechanism_cluster':kind,'source':'official_engine_probe',
                'types':[kind],'knowledge':knowledge,'target_action':target,'goal':goal,
                'public_goal':public_goal,'history':history,'initial_snapshot':str((folder/'initial.pkl').resolve()),
                'state_hash':state_digest(restore(start)),'snapshot_sha256':hashlib.sha256(start).hexdigest(),
                'initialization':initialization,'recipe_graph':{},'materials':{},'products':{},
                'witness':witness,'witness_length':len(witness),'witness_replay':checks[0]['trace'],
                'validated':True,'recoverable':True,'max_steps':40,'split':'test'})
    atomic_json(root/'cases.json',cases)
    atomic_json(root/'supplement_manifest.json',{'total_families':len(cases),'craft':30,'lock_release':3,'goal_switch':2,
        'dataset_hash':digest(cases),'scope':'Five official-mechanism diagnostic probes, not all long-chain hard cases. Robot Kingdom default disables tutorial and is excluded from goal-switch probes.',
        'unknown_dynamic_rules':'Native step rules, including object decay/reclamation, are retained. No invented dynamic action-rule changes.'})
    print(json.dumps({'families':len(cases),'hash':digest(cases)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(Path(a.output)/'supplement.log','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):build(a.output)
