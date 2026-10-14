"""User-authorized whitespace parsing repair, resumes saved original episodes."""
import argparse
import ast
import copy
import shutil
import subprocess
from .common import *


def original_assess():
    from agents.agc.control import Control
    commit=read(RESULTS/'execution.json')['freeze_commit']
    text=subprocess.check_output(['git','show',commit+':agents/agc/control.py'],cwd=ROOT,text=True)
    cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='Control')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='assess')
    namespace=dict(Control.assess.__globals__)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<frozen-original-assess>','exec'),namespace)
    return namespace['assess']


def prepare():
    offline()
    from agents.agc.control import Control
    from .preflight import Contracts,proposal,obs
    import unittest
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    assert result.wasSuccessful()
    c=Control();o=obs(feedback='First public fact.\nSecond public fact.');c.initialize(o)
    assert c.assess(proposal(quote='First public fact. Second public fact.'),o,True,1)[0]=='EXECUTE'
    assert c.assess(proposal(quote='First private fact. Second public fact.'),o,True,1)[2]
    assert c.assess(proposal(quote='First public fact? Second public fact.'),o,True,1)[2]
    checks=[]
    strict=original_assess()
    for game in ['remnant','mark']:
        out=RESULTS/'runs'/f'{game}__AGC';d=read(out/'decision_exhausted.json');c=Control.from_dict(copy.deepcopy(d['decision']['control_before']))
        p=d['decision']['attempts'][0]['proposal'];assert strict(c,p,d['observation'],True,d['step'])[2]
        assert c.assess(p,d['observation'],True,d['step'])[0]=='EXECUTE'
        checks.append(dict(game=game,resume_before_action=d['step'],old_rejected=True,new_accepts_existing_response=True,new_model_calls=0))
    overrides={n:dict(before=read(RESULTS/'freeze.json')['files'][n],after=sha(ROOT/n)) for n in ['agents/agc/control.py','scar_stage24/common.py']}
    write(RESULTS/'repair_freeze.json',dict(user_authorized=True,scope='Normalize only whitespace for evidence matching; preserve first attempts, resume original episodes.',
        overrides=overrides,new_files={'scar_stage24/repair.py':sha(Path(__file__))},checks=checks,
        policy_edit=dict(file='agents/agc/control.py',removed_lines=1,added_lines=2),new_model_calls_before_repair=0))
    print(json.dumps(checks))


def resume(game):
    check_freeze()
    import scar_stage24.run as runner
    prior=read(RESULTS/'runs'/f'{game}__AGC'/'summary.json')
    assert prior['status']=='agent_decision_exhausted'
    output=RESULTS/'resumed';initial=output/'initial'/game
    if not initial.exists():shutil.copytree(RESULTS/'initial'/game,initial)
    runtime=RUNTIME/'runs'/f'{game}__AGC'
    checkpoint=runtime/read(runtime/'latest.json')['checkpoint'];assert read(checkpoint/'meta.json')['step']==prior['steps']
    terminal=runtime/'decision_exhausted.json'
    if terminal.exists():terminal.rename(runtime/'decision_exhausted.first_pass.json')
    write(RESULTS/'repair_launch'/f'{game}.json',dict(game=game,resume_before_action=prior['steps']+1,
        immutable_prefix_steps=prior['steps'],old_requests=prior['requests'],old_cost_usd=prior['cost_usd'],
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        original_result=f'results/stage24/runs/{game}__AGC',unchanged_checkpoint_sha256=sha(checkpoint/'physical.pkl')))
    runner.RESULTS=output
    return runner.execute(game,str(ROOT.parent/'miyao.txt'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--game',choices=GAMES)
    args=p.parse_args()
    if args.prepare:prepare()
    else:resume(args.game)
