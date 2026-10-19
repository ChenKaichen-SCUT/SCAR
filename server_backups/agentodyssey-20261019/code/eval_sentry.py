"""Isolated evaluator adapter: factory replacement and post-outcome callback."""
from pathlib import Path
R=Path(__file__).resolve().parent
source=(R/'agentodyssey/eval.py').read_text()
old='("agents.long_context_agent",                   "create_long_context_agent")'
assert source.count(old)==1
source=source.replace(old,'("agents.sentry_agent",                         "create_sentry_agent")')
anchor='        env.update_config(cumulative=args.cumulative_config_save)\n'
assert source.count(anchor)==1
hook='''
        # Send only observed text, validity flag, and budget/episode termination.
        # Rewards and private state never enter Sentry.
        for sentry_host in env.agents:
            sentry_host.observe_outcome(
                obs[sentry_host.id]["text"],
                invalid_action=bool(invalids.get(sentry_host.id, False)),
                terminal=bool(done or env.steps >= args.max_steps),
            )
'''
source=source.replace(anchor,anchor+hook)
exec(compile(source,str(R/'agentodyssey/eval.py'),'exec'),
     {'__name__':'__main__','__file__':str(R/'agentodyssey/eval.py')})
