"""Public-only interpretation, fixed before new native outcomes.

An action identifier is not an intent identifier: identical moves may carry
different explicitly recorded goals. No family, hidden recipe or outcome enters
normalization. The caller supplies only contemporaneous public metadata.
"""
import copy
from scar.io import digest
from scar_stage12.public import controller, next_action
from scar_v3.state import parse_action


def recorded_goal(decision, action):
    """Read the method's own saved commitment; never borrow a rival's goal."""
    e=decision.get('mechanisms',{}).get('exploration') or {}
    source=e.get('source') or {}
    if source.get('product') and e.get('reason')=='acquire publicly named trial ingredient':
        return {'target':source['product'],'operation':'craft_inspect',
                'evidence':{'path':'mechanisms.exploration','value':e}}
    s=decision.get('stage11',{}).get('selected') or {}
    if s.get('kind')=='known_forward_bridge' and s.get('target'):
        p=parse_action(action); old=parse_action(s.get('action',''))
        if action==s.get('action') or (p.verb==old.verb=='craft' and p.target==old.target):
            return {'target':s['target'],'operation':'craft_inspect',
                    'evidence':{'path':'stage11.selected','value':s}}
    return None


def normalize(public, candidate, goal=None):
    c=copy.deepcopy(candidate); ctrl=controller(public['controller'],public['observation'])
    first=c.get('first_action') or c.get('next_action') or next_action(ctrl,c)
    assert first, c
    p=parse_action(first); kind=c['kind']; target=c['target']
    out={'first_action':first,'target':target,'evidence':[{'candidate':c}],
         'clarity':'explicit','location':c.get('location'), 'operation':None}
    if kind=='inspect': out.update(type='Inspect',operation='inspect')
    elif kind=='craft':
        out.update(type='Craft-and-Inspect' if p.verb=='craft' else 'Prepare-and-Explore',operation='craft_inspect')
    elif kind=='visit': out.update(type='Prepare-and-Explore',operation='visit_inspect')
    elif kind=='general':
        out.update(type='Move',operation='move',location=target,clarity='incomplete',
                   incompleteness='no specified exploration object after arrival')
    elif p.verb in {'store','pick up','take out'}:
        out.update(type='Acquire',operation='atomic',clarity='incomplete',
                   incompleteness='acquisition does not establish a downstream exploration goal')
    elif p.verb=='enter':
        out.update(type='Move',operation='move',location=p.target,clarity='incomplete',
                   incompleteness='destination alone does not establish an exploration goal')
    else:
        out.update(type='Atomic',operation='atomic',clarity='incomplete',
                   incompleteness='no supported continuation')
    # A recorded preparation goal is relevant only to a preparatory action.
    if goal and p.verb in {'store','pick up','take out','enter'}:
        out.update(type='Prepare-and-Explore',target=goal['target'],
                   operation=goal['operation'],clarity='explicit',location=goal.get('location'))
        out.pop('incompleteness',None);out['evidence'].append(goal['evidence'])
        if goal['operation']=='move':
            out.update(clarity='incomplete',incompleteness='explicit destination, no unique exploration object')
        if goal['operation']=='craft_inspect':
            out['public_recipe_at_start']=copy.deepcopy(ctrl.table.recipes.get(goal['target'],{}))
            out['recipe_relation_unknown']=not bool(out['public_recipe_at_start'].get('ingredients'))
    out['id']='i_'+digest({k:v for k,v in out.items() if k not in {'evidence','public_recipe_at_start'}})[:16]
    return out
