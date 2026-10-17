"""Check final narrow type-logic fixes on all recorded full-game decisions."""
import argparse,contextlib,json,sys,time
from pathlib import Path
from scar_public.run import build_agent
from scar_public.experiments.replay_action_compatibility import RecordedProvider,semantic_decision


def main():
    from scar.environment import restore
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--initial-root',type=Path,required=True);a=p.parse_args();results=[]
    for game in ('remnant','mark','metropolis'):
        pair=a.root/'corrected'/game;manifest=json.loads((pair/'manifest.json').read_text());run=pair/'v15'
        assert json.loads((run/'current.json').read_text())['complete']
        env=restore(a.initial_root/game/'initial.pkl',a.root/'replay_scratch'/game);provider=RecordedProvider()
        agent=build_agent('task_outcome_v15',env,provider);c=agent.resource_controller;c.context_scope='attributes';c.max_steps=300
        count=0;start=time.perf_counter()
        for path in sorted((run/'trace').glob('*.json')):
            row=json.loads(path.read_text());provider.step=row['step']-1;provider.calls=list(row['provider_calls'])
            with contextlib.redirect_stdout(sys.stderr):action,_,_,response=agent.act(dict(text=row['observation'],step=provider.step))
            assert not provider.calls and action==row['action'],(game,row['step'],action,row['action'])
            # Same semantic response, including chosen plans and certificates;
            # only the existing compute-time instrumentation is ignored.
            assert semantic_decision(json.loads(response))==semantic_decision(json.loads(row['response'])),(game,row['step'],'response changed')
            count+=1
        results.append(dict(game=game,matched_decisions=count,exact_prompt_hashes=True,new_api_requests=0,elapsed_s=time.perf_counter()-start))
    (a.root/'final_replay.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))


if __name__=='__main__':main()
