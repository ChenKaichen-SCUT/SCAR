"""Run the frozen evaluator with one in-memory factory substitution only."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'agentodyssey/eval.py').read_text()
old='("agents.long_context_agent",                   "create_long_context_agent")'
new='("agents.feedback_control_agent",               "create_feedback_control_agent")'
assert source.count(old)==1, 'Unexpected evaluator: refuse ambiguous substitution'
source=source.replace(old,new)
exec(compile(source,str(ROOT/'agentodyssey/eval.py'),'exec'),
     {'__name__':'__main__','__file__':str(ROOT/'agentodyssey/eval.py')})
