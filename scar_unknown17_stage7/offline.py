"""Pre-call gates: old-trace parity, real same-state physics, runner integration.

Teacher-forced decisions and local branches are development evidence, never
reported as model closed-loop success rates.
"""
import argparse
import contextlib
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from scar.environment import restore,AGENT_ID,snapshot,state_digest
from scar.diagnostics.build import transition
from scar.io import atomic_json
from scar_unknown17.audit import initial,branch
from scar_unknown17.controller import SimpleController
from scar_unknown17.facts import PublicFacts
from scar_unknown17.evaluate import one_action
from scar_sequence.prepare import NoAPIProvider
from scar_unknown17_stage7.controller import Stage7Controller,CONFIGS
from scar_unknown17_stage7.run import episode

OUT=Path('results/stage7')

def save_state(raw,label):
    path=OUT/'counterfactual_states'/f'{label}.pkl.gz';path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as f:f.write(raw)
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'serialized_sha256':hashlib.sha256(raw).hexdigest()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime);root.mkdir(parents=True,exist_ok=True)
    cs=json.loads((OUT/'cases.json').read_text());cases={c['id']:c for c in cs};parity=[];local=[];roundtrips=[];regressions=[]
    with (root/'offline.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for ep in map(json.loads,gzip.open('results/unknown17/trajectories_FIFOCombined.jsonl.gz','rt')):
            case=cases[ep['case_id']];old=SimpleController(True,'learned');controllers={m:Stage7Controller(**flags) for m,flags in CONFIGS.items()}
            for c in [old]+list(controllers.values()):
                for h in case['history']:c.observe(h['before'],h['action'],h['after'])
                c.set_goal(case['target_action'],case['public_goal']);c.events.clear()
            with tempfile.TemporaryDirectory() as tmp:
                env=restore(initial(case),tmp);seen=set()
                for r in ep['rows']:
                    i=r['index'];obs=r['observation'];base=r['proposed_action'];raw=None
                    old_action=old.choose(obs,base);choices={m:c.choose(obs,base) for m,c in controllers.items()}
                    same_state=all(controllers['C0'].to_dict()[k]==v for k,v in old.to_dict().items())
                    parity.append({'case_id':case['id'],'index':i,'action':old_action,
                        'matches_recorded':old_action==r['executed_action'],'C0_same_action':choices['C0']==old_action,'original_fields_exact':same_state})
                    for m in ['C1','C2','C3','C4']:
                        if m in seen or choices[m]==choices['C0']:continue
                        seen.add(m);raw=raw or snapshot(env)
                        local.append({'case_id':case['id'],'index':i,'module':m,'base_action':base,
                            'state':save_state(raw,f"old-{case['id']}-{i}-{m}"),
                            'original_action':choices['C0'],'modified_action':choices[m],
                            'original':branch(raw,[choices['C0']],case),'modified':branch(raw,[choices[m]],case),
                            'policy_state':copy.deepcopy(controllers[m].to_dict()),
                            'scope':'first changed decision per module/family under recorded-history teacher forcing; not full closed loop'})
                    if (case['id'],i) in [('sequence-48401b39ba565b57',6),('sequence-7e32e0ff916aaa50',25)]:
                        raw=raw or snapshot(env);target=r['executed_action'].split()[-1]
                        d=controllers['C4'];selected=d._batch_action('craft 1 '+target)
                        variants=[one_action(raw,f'craft {n} {target}',tmp) for n in [1,2]]
                        regressions.append({'case_id':case['id'],'index':i,'D_selected':selected,
                            'public_reason':copy.deepcopy(d.stage7_decision['D_batch']),
                            'state':save_state(raw,f"quantity-{case['id']}-{i}"),'variants':variants,
                            'full_step_variants':[branch(raw,[f'craft {n} {target}'],case) for n in [1,2]]})
                    for c in [old]+list(controllers.values()):
                        c.observe(obs,r['executed_action'],r['next_observation']);c.events.clear()
                    transition(env,r['executed_action'])
                for m,c in controllers.items():
                    data=json.loads(json.dumps(c.to_dict()));clone=Stage7Controller.from_dict(data)
                    roundtrips.append({'case_id':case['id'],'config':m,'identical':clone.to_dict()==data})
        # The two opposing batch suffixes are fixed historical evaluator examples.
        old_checks=json.loads(Path('results/unknown17/offline_counterfactuals.json').read_text())
        conflict=json.loads(Path('results/unknown17/overproduction_counterfactual.json').read_text())
        suffix_checks=[]
        for source,case,expected,label in [
            (old_checks[0],cases['sequence-48401b39ba565b57'],[False,True],'efficient_two'),
            (conflict,cases['sequence-7e32e0ff916aaa50'],[True,False],'overproduction')]:
            raw=gzip.decompress(Path(source['state']['path']).read_bytes())
            variants=[branch(raw,v['actions'],case) for v in source['variants']]
            suffix_checks.append({'name':label,'state':source['state'],'variants':variants,
                'expected_goals':expected,'passed':[v['goal'] for v in variants]==expected,
                'scope':'fixed historical evaluator continuation; not autonomous recovery'})
        # Previously produced but uncollected target: public-only final collection.
        source=old_checks[1];raw=gzip.decompress(Path(source['state']['path']).read_bytes())
        case=next(c for c in json.loads(Path('results/sequence/dataset/cases.json').read_text()) if c['id']=='sequence-7ef74a089f1ce41d')
        with tempfile.TemporaryDirectory() as tmp:
            env=restore(raw,tmp);c=Stage7Controller(resource_goal_guard=True)
            for h in case['history']:c.observe(h['before'],h['action'],h['after'])
            c.set_goal(case['target_action'],case['public_goal']);action=c.choose(env.obs[AGENT_ID],'inspect scrap_metal')
            final=branch(raw,[action],case)
            suffix_checks.append({'name':'final_collection','state':source['state'],'selected':action,'variant':final,
                'passed':final['goal'],'scope':'old completed-craft snapshot, single public collection decision; no formal extra steps'})
        # Same observation => exact same public summary and full model messages C0.
        from scar_unknown17.agent import make_agent as old_agent
        from scar_unknown17_stage7.agent import make_agent as new_agent
        class Capture(NoAPIProvider):
            def generate(self,*args,**kwargs):self.last=(copy.deepcopy(args),copy.deepcopy(kwargs));return super().generate(*args,**kwargs)
        cfg=json.loads(Path('configs/protocol_stage7.json').read_text());case=cs[0];pa,pb=Capture(),Capture()
        with tempfile.TemporaryDirectory() as tmp:
            aa=old_agent('FIFOCombined',case['game'],pa,cfg,Path(tmp)/'a');bb=new_agent('C0',case['game'],pb,cfg,Path(tmp)/'b')
            for ag in [aa,bb]:
                ag.cfg.system_prompt+='\nExperiment recovery objective (priority for this episode): '+case['public_goal']
                for h in case['history']:
                    ag.memorize(f"{h['before']['text']}\nAction: {h['action']}\n{h['after']['text']}");ag.observe_transition(h['before'],h['action'],h['after'])
                ag.memorize('Recovery objective: '+case['public_goal']);ag.set_recovery_objective(case['target_action'],case['public_goal'])
            env=restore(initial(case),tmp);ob=env.obs[AGENT_ID]
            a1=aa.act(ob)[0];a2=bb.act(ob)[0]
            prompt_check={'same_model_call':pa.last==pb.last,'same_action':a1==a2,'same_memory':aa.short_term_memory==bb.short_term_memory,
                          'same_fact_summary':aa.decision['fact_summary']==bb.decision['fact_summary'],'api_calls':0}
        # All six actual agents + real runner + load/continue checkpoint, zero calls.
        integration=[];(root/'initials').mkdir(exist_ok=True);path=root/'initials'/f'{case["id"]}.pkl';path.write_bytes(initial(case))
        for m in CONFIGS:
            task=dict(case,task_id='smoke-'+m,algorithm=m,diagnostic=True,max_steps=2,stage='smoke',
                protocol_cohort='zero_api_integration',initial_snapshot=str(path))
            result=episode(task,cfg,root/'integration',None,1,provider_factory=NoAPIProvider)
            integration.append({k:result[k] for k in ['algorithm','status','steps','api_calls','cost_usd','error']})
    for name,data in [('original_parity',parity),('checkpoint_roundtrips',roundtrips),('quantity_regressions',regressions),
        ('fixed_suffix_checks',suffix_checks),('prompt_parity',prompt_check),('integration_checks',integration)]:atomic_json(OUT/(name+'.json'),data)
    with gzip.open(OUT/'offline_decisions.jsonl.gz','wt') as f:
        for x in local:f.write(json.dumps(x,ensure_ascii=False)+'\n')
    result={'api_calls':0,'parity_actions':len(parity),'original_parity_passed':all(all(x[k] for k in ['matches_recorded','C0_same_action','original_fields_exact']) for x in parity),
        'checkpoint_roundtrips':len(roundtrips),'roundtrips_passed':all(x['identical'] for x in roundtrips),
        'local_single_steps':len(local),'fixed_suffix_passed':all(x['passed'] for x in suffix_checks),
        'quantity_choices':[{k:x[k] for k in ['case_id','D_selected']} for x in regressions],
        'quantity_regressions_passed':[x['D_selected'].split()[1] for x in regressions]==['1','2'],
        'prompt_parity_passed':all(v for k,v in prompt_check.items() if k!='api_calls'),
        'integration_passed':all(x['status']=='completed' and x['api_calls']==0 for x in integration),
        'unit_test_report':'results/stage7/unit_tests.xml','formal_results_used_for_tuning':False}
    result['passed']=all(v for k,v in result.items() if k.endswith('_passed'))
    atomic_json(OUT/'offline_checks.json',result);print(json.dumps(result));assert result['passed']

if __name__=='__main__':main()
