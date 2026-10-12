"""Post-hoc zero-API checks of negative interactions in the frozen cohort.

Selection includes every C0-success -> C3/C5-failure family, plus the unique D
one-step goal regression and the observed repeated phantom pickup. No paid runs.
"""
import argparse
import contextlib
import copy
import gzip
import json
from pathlib import Path
from scar.environment import restore,AGENT_ID,state_digest
from scar.io import atomic_json
from scar_unknown17.audit import branch
from scar_unknown17_stage7.offline import save_state
from scar_unknown17_stage7.controller import Stage7Controller


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime);out=Path('results/stage7')
    cs={c['id']:c for c in json.loads((out/'cases.json').read_text())};records=[]
    eps={m:{e['case_id']:e for e in map(json.loads,gzip.open(out/f'trajectories_{m}.jsonl.gz','rt'))} for m in ['C0','C1','C3','C5']}
    with (root/'critical-checks.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for method in ['C3','C5']:
            for cid,ep in eps[method].items():
                if not eps['C0'][cid]['summary']['recovery_at_40'] or ep['summary']['recovery_at_40']:continue
                # First ready-craft on a state already showing that product on ground.
                candidates=[r for r in ep['rows'] if r.get('structured',{}).get('stage7',{}).get('C_ready_execution') and
                    (r['structured']['resource_table']['state'].get('ground') or {}).get(r['executed_action'].split()[-1],0)>0]
                if not candidates:continue
                r=candidates[0];i=r['index'];folder=root/'runs'/ep['task_id'];raw=(folder/'steps'/f'{i:04}'/'environment.pkl').read_bytes()
                ctrl=Stage7Controller.from_dict(r['stage7_state_before']);ctrl.flags['explore_execute_switch']=False
                alternate=ctrl.choose(r['observation'],r['proposed_action'])
                suffix=['craft 1 '+cs[cid]['goal']['name'],'pick up '+cs[cid]['goal']['name']]
                records.append({'kind':'all_C0_success_to_C3_or_C5_failure_redundant_craft','case_id':cid,'method':method,'index':i,
                    'state':save_state(raw,ep['task_id']+'-redundant-craft'),'base_proposal':r['proposed_action'],
                    'original_action':r['executed_action'],'C_off_action':alternate,
                    'original_fixed_suffix':branch(raw,[r['executed_action']]+suffix,cs[cid]),
                    'C_off_fixed_suffix':branch(raw,[alternate]+suffix,cs[cid]),
                    'scope':'same-state one-switch decision, same evaluator-supplied two-action goal suffix within40; not autonomous rerun'})
        # Unique local D false priority identified by exhaustive decision audit.
        for r in map(json.loads,gzip.open(out/'decision_counterfactuals.jsonl.gz','rt')):
            if r['flag']!='resource_goal_guard' or not r['changed'] or r.get('alternate_policy_error'):continue
            active,inactive=(r['original_effect'],r['alternate_effect']) if r['original_flags'][r['flag']] else (r['alternate_effect'],r['original_effect'])
            if inactive['physical_after']['goal'] and not active['physical_after']['goal']:
                folder=root/'runs'/r['task_id'];i=r['index'];raw=(folder/'initial.pkl' if i==0 else folder/'steps'/f'{i:04}'/'environment.pkl').read_bytes()
                records.append({'kind':'all_D_local_goal_regressions','case_id':r['case_id'],'index':i,'task_id':r['task_id'],
                    'state':save_state(raw,r['task_id']+'-D-local-regression'),'D_on':branch(raw,[active['action']],cs[r['case_id']]),
                    'D_off':branch(raw,[inactive['action']],cs[r['case_id']]),'scope':'actual single-step physical goal, no continuation'})
        for cid,ep in eps['C5'].items():
            sequence=[r for r in ep['rows'] if r.get('structured',{}).get('stage7',{}).get('D_goal') and r['semantic_rejection']]
            if not sequence:continue
            first=sequence[0];i=first['index'];folder=root/'runs'/ep['task_id'];raw=(folder/'initial.pkl' if i==0 else folder/'steps'/f'{i:04}'/'environment.pkl').read_bytes();env=restore(raw)
            area=env.world.area_instances[env.curr_agents_state['area'][AGENT_ID]]
            phantom={k:n for k,n in area.objects.items() if k not in env.world.objects}
            records.append({'kind':'all_C5_rejected_final_priorities','case_id':cid,'task_id':ep['task_id'],'indices':[r['index'] for r in sequence],
                'state':save_state(raw,ep['task_id']+'-final-priority-rejections'),'public_observation':env.obs[AGENT_ID],
                'engine_unknown_object_ids':phantom,'engine_mirage_records':env.world.auxiliary.get('salt_mirage'),
                'actual':branch(raw,[first['executed_action']],cs[cid]),'base':branch(raw,[first['proposed_action']],cs[cid]),
                'scope':'evaluator identifies phantom after policy decision; policy should react to public rejection without hidden IDs'})
    atomic_json(out/'critical_counterfactuals.json',{'api_calls':0,'checks':records,
        'selection':'all C0 success -> C3/C5 failures with ready-craft while copies grounded; all local D goal losses; all C5 rejected final priorities',
        'policy_frozen_unchanged':True})
    print(json.dumps({'checks':len(records),'api_calls':0,'kinds':[r['kind'] for r in records]}))

if __name__=='__main__':main()
