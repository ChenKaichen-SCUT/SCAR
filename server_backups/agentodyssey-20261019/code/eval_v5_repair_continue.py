"""Reconstruct prefix locally; exact public-transition check before new decisions."""
import json,os
import v5_full500_runtime
from pathlib import Path
R=Path(__file__).resolve().parent
past=[json.loads(x) for x in Path(os.environ['AO_REPLAY_AGENT_LOG']).read_text().splitlines() if x]
def verify_prefix(env,agent_log_paths):
    if env.steps>len(past):return
    for path in agent_log_paths.values():
        row=json.loads(Path(path).read_text().splitlines()[-1]);old=past[env.steps-1]
        for field in ['step','action','observation','next_observation','reward']:
            assert row.get(field)==old.get(field),('Saved trajectory reconstruction diverged before fresh API calls',env.steps,field)
    if env.steps==len(past):
        Path(os.environ['AO_REPLAY_RECEIPT']).write_text(json.dumps({'prefix_steps_verified':len(past),'all_actions_observations_rewards_identical':True,'new_provider_calls_for_prefix':0}))
source=(R/'agentodyssey/eval.py').read_text();old='("agents.long_context_agent",                   "create_long_context_agent")';assert source.count(old)==1
source=source.replace(old,'("agents.feedback_v5_agent",                    "create_feedback_v5_agent")')
anchor='        env.update_config(cumulative=args.cumulative_config_save)\n';assert source.count(anchor)==1
source=source.replace(anchor,anchor+'''
        verify_prefix(env, agent_log_paths)
        if done or env.steps >= args.max_steps:
            for ledger_host in env.agents:
                ledger_host.observe_final(obs[ledger_host.id]["text"])
''')
exec(compile(source,str(R/'agentodyssey/eval.py'),'exec'),{'__name__':'__main__','__file__':str(R/'agentodyssey/eval.py'),'verify_prefix':verify_prefix})
