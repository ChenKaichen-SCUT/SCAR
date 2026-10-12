"""Zero-API development gates on historical states only; never new test tasks."""
import argparse,copy,contextlib,gzip,hashlib,json,time,tempfile
from pathlib import Path
from scar.io import atomic_json,digest
from scar.environment import restore,snapshot,AGENT_ID,state_digest
from scar.diagnostics.build import transition
from scar_unknown17.audit import initial,branch
from scar_unknown17_stage7.controller import Stage7Controller,CONFIGS
from scar_stage8.controller import ReliableController,HISTORICAL,make_controller,restore_controller
OUT=Path('results/stage8')

def save_state(raw,label):
    path=OUT/'counterfactual_states'/f'{label}.pkl.gz';path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as f:f.write(raw)
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'serialized_sha256':hashlib.sha256(raw).hexdigest()}

def adapted(state,method):
    data=copy.deepcopy(state);data.update(flags=CONFIGS[HISTORICAL[method]],method=method,safety=True)
    return ReliableController.from_dict(data)

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime);root.mkdir(parents=True,exist_ok=True);OUT.mkdir(exist_ok=True)
    cases={c['id']:c for c in json.loads(Path('results/stage7/cases.json').read_text())};eps={}
    for m in CONFIGS:
        for e in map(json.loads,gzip.open(f'results/stage7/trajectories_{m}.jsonl.gz','rt')):eps[m,e['case_id']]=e
    parity=[];audits=[];roundtrips=[];gate=[]
    with (root/'offline.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        # Inspect every old committed Robot Kingdom state, including all failures.
        for (m,cid),ep in eps.items():
            c=cases[cid]
            if c['game']!='robot_kingdom':continue
            ctrls={k:make_controller(k) for k in ['P3','P4']}
            for ctrl in ctrls.values():
                for h in c['history']:ctrl.observe(h['before'],h['action'],h['after'])
                ctrl.set_goal(c['target_action'],c['public_goal'])
            with tempfile.TemporaryDirectory() as tmp:
                env=restore(initial(c),tmp)
                for row in ep['rows']:
                    state=row['stage7_state_before'];base=row['proposed_action'];obs=row['observation'];i=row['index']
                    legacy=Stage7Controller.from_dict(state);off=ReliableController.from_dict(dict(state,safety=False))
                    expected=legacy.choose(obs,base);got=off.choose(obs,base)
                    parity.append({'method':m,'case_id':cid,'index':i,'passed':got==expected==row['executed_action']})
                    raw=None
                    for method,ctrl in ctrls.items():
                        before=copy.deepcopy(ctrl.to_dict());tick=time.monotonic();action=ctrl.choose(obs,base);elapsed=time.monotonic()-tick
                        clone=restore_controller(json.loads(json.dumps(before)));same=clone.choose(obs,base)==action
                        roundtrips.append({'case_id':cid,'method':method,'historical_method':m,'index':i,'same_next_action':same,
                            'bounded':elapsed<1 and ctrl.depth_peak<=ctrl.MAX_DEPTH and ctrl.search_nodes<=ctrl.MAX_NODES+1,
                            'seconds':elapsed})
                        ground=ctrl.table.state.get('ground') or {};pact=row['executed_action'].split()[-1]
                        error=row['semantic_rejection'] or (row.get('proposed_effect') or {}).get('physical_goal') and not row['diagnostic_goal_reached'] or (row['executed_action'].startswith('craft ') and ground.get(pact,0)>0)
                        if error and action!=row['executed_action']:
                            raw=raw or snapshot(env)
                            audits.append({'case_id':cid,'old_method':m,'new_method':method,'index':i,'base':base,
                                'original_action':row['executed_action'],'new_action':action,'original_feedback':row['action_rule_feedback'],
                                'state':save_state(raw,f'{m}-{cid}-{i}') ,'old':branch(raw,[row['executed_action']],c),
                                'new':branch(raw,[action],c),'safety':copy.deepcopy(ctrl.safety_decision),
                                'scope':'historical teacher forcing, not closed-loop task success'})
                        ctrl.observe(obs,row['executed_action'],row['next_observation']);ctrl.events.clear()
                    transition(env,row['executed_action'])
        critical=json.loads(Path('results/stage7/critical_counterfactuals.json').read_text())['checks']
        for ck in critical:
            c=cases[ck['case_id']];raw=gzip.decompress(Path(ck['state']['path']).read_bytes());env=restore(raw)
            if ck['kind'].startswith('all_C0'):
                row=eps[ck['method'],c['id']]['rows'][ck['index']];suffix=['craft 1 '+c['goal']['name'],'pick up '+c['goal']['name']]
            elif ck['kind']=='all_D_local_goal_regressions':
                row=eps['C1',c['id']]['rows'][ck['index']];suffix=[]
            else:
                row=eps['C5',c['id']]['rows'][ck['indices'][0]];suffix=[]
            for method in ['P3','P4']:
                ctrl=adapted(row['stage7_state_before'],method);action=ctrl.choose(env.obs[AGENT_ID],row['proposed_action'])
                old=branch(raw,[row['executed_action']]+suffix,c);new=branch(raw,[action]+suffix,c)
                if ck['kind'].startswith('all_C5'):
                    # Execute original rejected pickup, then test exact unchanged conditions.
                    ctrl.observe(row['observation'],row['executed_action'],row['next_observation'])
                    action2=ctrl.choose(row['next_observation'],row['executed_action'])
                    passed=action2!=row['executed_action'];extra={'after_rejection_action':action2}
                else:passed=new['goal'];extra={}
                gate.append({'kind':ck['kind'],'case_id':c['id'],'method':method,'state':ck['state'],
                    'old_action':row['executed_action'],'new_action':action,'old':old,'new':new,'passed':passed,**extra})
        # Required overproduction regression on the old exact physical checkpoint.
        over=json.loads(Path('results/unknown17/overproduction_counterfactual.json').read_text())
        c=cases['sequence-7e32e0ff916aaa50'];raw=gzip.decompress(Path(over['state']['path']).read_bytes())
        ep=next(x for x in map(json.loads,gzip.open('results/unknown17/trajectories_FIFOCombined.jsonl.gz','rt')) if x['case_id']==c['id'])
        for method in ['P3','P4']:
            ctrl=make_controller(method)
            for h in c['history']:ctrl.observe(h['before'],h['action'],h['after'])
            ctrl.set_goal(c['target_action'],c['public_goal'])
            for row in ep['rows'][:25]:
                ctrl.choose(row['observation'],row['proposed_action']);ctrl.observe(row['observation'],row['executed_action'],row['next_observation'])
            ctrl.table.observe(ep['rows'][25]['observation'])
            selected=ctrl.protect_craft('craft 2 astrolabe_core','craft 2 astrolabe_core')
            variants={x['actions'][0]:x['actions'] for x in over['variants']}
            new=branch(raw,variants.get(selected,[selected]),c)
            old=branch(raw,variants['craft 2 astrolabe_core'],c)
            gate.append({'kind':'orrery_overproduction','method':method,'state':over['state'],'old_action':'craft 2 astrolabe_core',
                'new_action':selected,'old':old,'new':new,'passed':selected=='craft 1 astrolabe_core' and new['goal'] and not old['goal'],
                'scope':'quantity safety decision plus pre-existing fixed evaluator suffix, not policy recovery'})
        abort=json.loads(Path('results/stage7/method_terminations.json').read_text())['terminations'][0]
        raw=gzip.decompress(Path(abort['checkpoint']['path']).read_bytes());original_error=None
        try:Stage7Controller.from_dict(abort['controller_before_abort']).choose(abort['public_observation'],abort['base_proposal_at_abort'])
        except RecursionError:original_error='RecursionError'
        for m in ['P3','P4']:
            ctrl=adapted(abort['controller_before_abort'],m);tick=time.monotonic();action=ctrl.choose(abort['public_observation'],abort['base_proposal_at_abort']);elapsed=time.monotonic()-tick
            effect=branch(raw,[action],cases[abort['case_id']])
            gate.append({'kind':'original_abort','method':m,'state':abort['checkpoint'],'old_error':original_error,'new_action':action,
                'new':effect,'seconds':elapsed,'search':ctrl.safety_decision,'passed':original_error=='RecursionError' and elapsed<1 and bool(action)})
    with gzip.open(OUT/'historical_state_audits.jsonl.gz','wt') as f:
        for r in audits:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    for name,data in [('historical_parity',parity),('checkpoint_roundtrips',roundtrips),('critical_regressions',gate)]:atomic_json(OUT/(name+'.json'),data)
    checks={'api_calls':0,'old_robot_decisions':len(parity),'historical_error_counterfactuals':len(audits),
        'parity_passed':all(x['passed'] for x in parity),'bounded_and_roundtrip_passed':all(x['same_next_action'] and x['bounded'] for x in roundtrips),
        'critical_passed':all(x['passed'] for x in gate),'critical_count':len(gate),
        'new_test_results_seen':False,'scope':'all six old Robot histories plus explicitly required cross-game legacy unit snapshots; no model rollout outside Robot'}
    checks['passed']=all(v for k,v in checks.items() if k.endswith('_passed'));atomic_json(OUT/'offline_checks.json',checks);print(json.dumps(checks));assert checks['passed']
if __name__=='__main__':main()
