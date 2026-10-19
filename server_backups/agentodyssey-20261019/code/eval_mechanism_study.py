"""Use the original environment/evaluator with a process-local agent factory replacement."""
from pathlib import Path
R=Path(__file__).resolve().parent
source=(R/'agentodyssey/eval.py').read_text()
old='("agents.long_context_agent",                   "create_long_context_agent")'
assert source.count(old)==1
source=source.replace(old,'("agents.mechanism_study_agent",               "create_mechanism_study_agent")')
anchor='        env.update_config(cumulative=args.cumulative_config_save)\n'
assert source.count(anchor)==1
source=source.replace(anchor,anchor+'''
        if done or env.steps >= args.max_steps:
            for ledger_host in env.agents:
                ledger_host.observe_final(obs[ledger_host.id]["text"])
''')
exec(compile(source,str(R/'agentodyssey/eval.py'),'exec'),{'__name__':'__main__','__file__':str(R/'agentodyssey/eval.py')})
