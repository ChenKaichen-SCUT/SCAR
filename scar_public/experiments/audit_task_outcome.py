"""No-API public-history audit at the previously selected V14 checkpoint."""
import argparse,json
from pathlib import Path
from scar_public.action_history import historical_intents
from scar_public.task_outcome import OutcomeMemory,OutcomeController


def main():
    p=argparse.ArgumentParser();p.add_argument('checkpoint',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    cp=a.checkpoint;step=int(cp.name);saved=json.loads((cp/'agent.json').read_text());saved.update(historical_intents(cp))
    m=OutcomeMemory();m.load(saved);c=OutcomeController(m);c.context_scope='attributes'
    text=json.loads((cp.parent.parent/'trace'/f'{step+1:04d}.json').read_text())['observation']
    m.prompt(text);c.resume(text);c.prepare_decision(text,step);selected=c.method_condition_step(text,step)
    out=dict(api_requests=0,selected=selected,decisions=m.outcome_decisions,focus=m.outcome_focus)
    a.output.write_text(json.dumps(out,indent=2));print(json.dumps(dict(action=selected['action'] if selected else None,focus=m.outcome_focus,api_requests=0)))


if __name__=='__main__':main()
