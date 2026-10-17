"""Require real pre-LLM action exposure before launching another paid run."""
import argparse,json
from pathlib import Path
from scar_public.action_repair import ActionMemory,ActionController
from scar_public.action_history import historical_intents

def main():
    p=argparse.ArgumentParser();p.add_argument('checkpoint',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    cp=a.checkpoint;step=int(cp.name);state=json.loads((cp/'agent.json').read_text());warm=historical_intents(cp)
    state.update(warm);m=ActionMemory();m.load(state);c=ActionController(m);c.context_scope='attributes'
    row=json.loads((cp.parent.parent/'trace'/f'{step+1:04d}.json').read_text());text=row['observation']
    m.prompt(text);c.resume(text);c.prepare_decision(text,step);action=c.method_condition_step(text,step)
    out=dict(step=step,bindings=warm['action_goal_bindings'],action=action,compilations=m.action_compilations,api_requests=0)
    a.output.write_text(json.dumps(out,indent=2));print(json.dumps(dict(step=step,action=action['action'] if action else None,bindings=len(warm['action_goal_bindings']),api_requests=0)))
    assert action and action['decision_source']=='evidence_action_program'

if __name__=='__main__':main()
