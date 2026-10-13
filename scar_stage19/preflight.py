"""Zero-API unit tests and selected historical native-state regression."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from .common import ROOT, RESULTS, write, load, sha, read_gzip, gzip_rows, deny_network
from .controller import Controller19
from .agent import make_method
from .tests.test_planning import CaptureProvider, proposal


def main():
    deny_network()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'scar_stage19/tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    from scar.environment import AGENT_ID, snapshot, restore, state_digest
    from scar_stage17.environment import create_initial
    from scar_stage17.evaluate import native_step
    from scar.io import digest
    tasks=load(RESULTS/'tasks.json'); cases=[]; integration=[]; factual=0
    # Prior outcomes select engineering edge cases, never new policy rollouts.
    for game in ('robot_kingdom','quarantine'):
        candidates=[]
        for task in [t for t in tasks if t['game_name']==game]:
            rows=read_gzip(ROOT/'results/stage18/runs'/f"{task['task_id']}__SCAR18/trajectory.jsonl.gz")
            special=[r['step'] for r in rows if 'Missing necessary' in r['feedback']['text']]
            if special: candidates.append((task, rows, special))
        # One native missing-precondition trajectory and one short success/game.
        selected=candidates[:1]
        # Explicit requested engineering case: public prerequisite construction
        # at a previously diagnosed sharpened_blade state, never a policy rule.
        selected += [entry for entry in candidates[1:] if entry[0]['target_item']=='sharpened_blade']
        success=[]
        for task in [t for t in tasks if t['game_name']==game]:
            folder=ROOT/'results/stage18/runs'/f"{task['task_id']}__SCAR18"
            summary=load(folder/'summary.json')
            if summary['success']:success.append((summary['steps'],task,folder))
        _,task,folder=min(success,key=lambda x:x[0])
        rows=read_gzip(folder/'trajectory.jsonl.gz')
        selected.append((task,rows,[1,len(rows)]))
        for task, rows, selected_steps in selected:
            with tempfile.TemporaryDirectory(prefix='scar19-preflight-') as directory:
                root=Path(directory)
                with contextlib.redirect_stdout(io.StringIO()):
                    env,history=create_initial(game,task['initial_seed'],root/'initial')
                assert state_digest(env)==task['initial_state_hash'] and digest(history)==task['initial_public_history_hash']
                c=Controller19()
                for h in history:c.observe(h['before'],h['action'],h['after'])
                c.set_goal('craft 1 '+task['target_item'],task['objective_text'])
                for row in rows:
                    assert state_digest(env)==row['physical_before']['state_hash']
                    factual_snapshot=snapshot(env)
                    c.table.observe(row['observation'])
                    if row['step'] in selected_steps or row['step']-1 in selected_steps:
                        trial=Controller19.from_dict(json.loads(json.dumps(c.to_dict())))
                        recovered=Controller19.from_dict(json.loads(json.dumps(c.to_dict())))
                        action=trial.choose(row['observation'])
                        assert recovered.choose(row['observation'])==action
                        assert recovered.to_dict()==trial.to_dict()
                        assert trial.target==c.target and not hasattr(trial,'consequences')
                        item=dict(task_id=task['task_id'],step=row['step'],selected_action=action,
                            ask_planner=action is None, audit=trial.audit19,blocker=trial.blocker19,
                            original_action=row['action'],source_state_hash=state_digest(env),
                            save_restore_next_action_equal=True)
                        if action:
                            clone=restore(snapshot(env)); target=clone.world.auxiliary['obj_name_to_id'][task['target_item']]
                            (oa,ra,da,ia),_=native_step(clone,action,target);clone.update_scores(ra)
                            trial.observe(row['observation'],action,oa[AGENT_ID])
                            assert trial.step16==c.step16+1
                            item.update(alternate_feedback=oa[AGENT_ID],alternate_done=bool(da),
                                        alternate_state_hash=state_digest(clone))
                        cases.append(item)
                    # Always continue the original archived action and RNG, never
                    # feed alternate observations into the historical controller.
                    env=restore(factual_snapshot)
                    out,reward,done,info=env.step({AGENT_ID:row['action']});env.update_scores(reward)
                    assert out[AGENT_ID]==row['feedback'] and state_digest(env)==row['state_hash']
                    c.observe(row['observation'],row['action'],row['feedback']);factual+=1
                with contextlib.redirect_stdout(io.StringIO()):
                    # Factory/checkpoint contract, with no provider calls allowed.
                    agent=make_method('SCAR19',game,CaptureProvider(),task['objective_text'],task['target_item'],history,root/'memory')
                    cp=root/'saved';agent.controller=c;agent.save_memory(str(cp))
                    restored=make_method('SCAR19',game,CaptureProvider(),task['objective_text'],task['target_item'],history,root/'other')
                    restored.load_memory(str(cp))
                assert agent.controller.to_dict()==restored.controller.to_dict()
                integration.append(dict(task=task['task_id'],game=game,agent_memory_restored=True))
    # Run a few real native steps through the new agent, answering any knowledge
    # gap with a captured structured inspection. This is acceptance, not scoring.
    with tempfile.TemporaryDirectory(prefix='scar19-agent-') as directory:
        task=tasks[0]; root=Path(directory)
        env,history=create_initial(task['game_name'],task['initial_seed'],root/'initial')
        class PlannerFixture(CaptureProvider):
            def generate(self, **kwargs):
                visible=[n for n in sorted(agent.controller.visible()) if n not in agent.controller.table.inspected]
                self.reply=proposal('INSPECT_OBJECT',visible[0])
                return super().generate(**kwargs)
        provider=PlannerFixture()
        agent=make_method('SCAR19',task['game_name'],provider,task['objective_text'],task['target_item'],history,root/'agent')
        env=restore(snapshot(env),root/'world',agent=agent)
        for step in range(6):
            before=copy.deepcopy(env.obs[AGENT_ID]);action,*_=agent.act(before)
            out,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
            agent.observe_transition(before,action,out[AGENT_ID])
            assert agent.controller.step16==step+1
        assert provider.calls and len(provider.calls)<6
        integration.append(dict(real_agent_native_steps=6, mock_subgoal_requests=len(provider.calls),
                                 controller_only_steps=6-len(provider.calls),api_calls=0))
    gzip_rows(RESULTS/'preflight_branches.jsonl.gz',cases)
    receipt=dict(passed=True,unit_tests=result.testsRun,api_calls=0,network_disabled=True,
        historical_factual_steps=factual,selected_states=len(cases),integration=integration,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scar_stage19').rglob('*.py')},
        scope='small engineering checks and one-step historical branches; no new formal episode or tuning to new scores')
    write(RESULTS/'preflight_local.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_hashes'}))


if __name__=='__main__':main()
