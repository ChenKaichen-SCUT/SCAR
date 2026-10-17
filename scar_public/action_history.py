"""Warm a new intention registry from the complete recorded public prefix."""
import json
from pathlib import Path
from scar_public.action_repair import ActionMemory,ActionController


def prefix_rows(checkpoint):
    """A resumed run's local trace omits its ancestor's public prefix."""
    manifest=json.loads((checkpoint.parent.parent/'manifest.json').read_text())
    fork=manifest.get('diagnostic_fork')
    if fork:yield from prefix_rows(Path(fork['path']))
    for path in sorted((checkpoint.parent.parent/'trace').glob('*.json')):
        if int(path.stem)>int(checkpoint.name):break
        yield json.loads(path.read_text())


def historical_intents(checkpoint):
    """Warm only the new registry from recorded public decisions up to the fork."""
    m=ActionMemory();c=ActionController(m);c.intervention_mode='observe'
    last=0
    for r in prefix_rows(checkpoint):
        assert r['step']==last+1,('Missing public prefix',last,r['step'])
        last=r['step'];parsed=json.loads(r['response']);step=r['step']-1
        m.prompt(r['observation']);c.prepare_decision(r['observation'],step)
        c.assess(parsed,step,'historical_public_intent');m.update(parsed,r['observation'],step)
    assert last==int(checkpoint.name)
    return dict(intent_tasks=m.intent_tasks,intent_anchors=m.intent_anchors,
        intent_observed_count=m.intent_observed_count,action_goal_bindings=m.action_goal_bindings)
