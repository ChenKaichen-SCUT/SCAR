"""Offline routing check, then start exactly the explicitly requested three runs."""
import json,subprocess
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');py=str(R/'.venv/bin/python')
assert not (R/'v5_three_games_protocol.json').exists(),'Already registered; inspect existing batch, never launch again'
test=subprocess.run([py,str(R/'test_v5_batch_transport.py')],capture_output=True,text=True);assert test.returncode==0,test.stderr
dry=subprocess.run([py,str(R/'run_v5_three_games.py')],capture_output=True,text=True);assert dry.returncode==0,dry.stderr
(R/'v5_batch_transport_preflight.json').write_text(json.dumps({'all_passed':True,'real_provider_calls':0,'test_output':test.stderr,'dry_run':json.loads(dry.stdout)},indent=2))
with (R/'v5_three_games_supervisor.log').open('x') as out:
    p=subprocess.Popen([py,'-u',str(R/'run_v5_three_games.py'),'--execute'],cwd=R,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
(R/'v5_three_games_supervisor.pid').write_text(str(p.pid));print(json.dumps({'launched_pid':p.pid,'batch_limits':json.loads(dry.stdout)['batch_limits'],'per_game_limits':json.loads(dry.stdout)['per_game_limits'],'v5_algorithm_unchanged':True}))
