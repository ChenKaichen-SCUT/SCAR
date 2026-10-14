"""Public-evidence recovery-chain rubric. Analysis only; never an Agent input."""
import re
from collections import Counter
from agents.agc.state import extract
from scar_stage27.grade import RUBRIC
from .common import *

UNSUPPORTED={'not_equippable','container_nesting','not_writable','unknown_object','not_craftable','not_edible'}
GAP={
 'hand_capacity':r'hand|space|capacity|carry|inventory|room',
 'container_capacity':r'bag|satchel|container|space|capacity|stor',
 'missing_lockpick_tool':r'lockpick|lock.pick|key',
 'missing_writing_tool':r'writing tool|writing implement|pen',
 'missing_workbench':r'workbench', 'missing_furnace':r'furnace',
 'insufficient_ingredients':r'ingredient|material|recipe',
 'locked_exit':r'key|unlock|lockpick|locked',
 'combat_blocks_exit':r'goblin|vulture|raider|stalker|enemy|enemies|combat|block|escape|surviv',
 'target_not_held':r'paper|hand|hold', 'object_not_held_or_visible':r'hand|hold|pick|locat|find|object|target|inspect',
 'no_path':r'route|path|neighbor|adjacen|hall', 'container_nesting':r'container|bag|satchel|hand|space',
 'equipment_slot_occupied':r'unequip|container|bag|satchel|slot', 'not_writable':r'writ|paper|surface|note',
 'unknown_object':r'recipe|craftable|valid|weapon|item', 'object_unavailable':r'locat|container|bag|satchel|hand|target|find',
 'not_craftable':r'recipe|craftable|obtain|find|alternative', 'not_edible':r'food|edible|heal|apple|bread',
 'not_equippable':r'equippable|equip|gear|weapon|armor|alternative', 'unspecified_rejection':r'unknown|unclear|inspect|check',
}
INTENT=r'\b(?:need to|must|should|will|shall|try to|have to|want to|free|obtain|acquire|find|locate|gather|collect|manage|resolve|secure|clear|defeat|survive|equip|unequip|return|move|identify|search|check|learn|inspect)\b'
ACTION_VERBS={
 'hand_capacity':{'drop','store','equip','unequip','eat','discard','disassemble'},
 'container_capacity':{'inspect','take','discard','equip','unequip','drop'},
 'missing_lockpick_tool':{'inspect','pick','take','craft','enter','talk','buy'},
 'missing_writing_tool':{'inspect','pick','take','store','drop','equip'},
 'missing_workbench':{'enter','inspect','pick','take','craft','store','drop'},
 'missing_furnace':{'enter','inspect','pick','take','craft','store','drop'},
 'insufficient_ingredients':{'inspect','pick','take','craft','enter','store','drop','buy','disassemble'},
}

def intent(s,proposal):
    typ=s['failure_type'];goal=str(proposal.get('goal_description',''));reason=str(proposal.get('reasoning',''))
    p,q,_=RUBRIC[typ];understood=bool(re.search(p,reason,re.I) and re.search(q,reason,re.I))
    gap=GAP[typ]
    def recovery_text(text):
        if not re.search(gap,text,re.I) or not re.search(INTENT,text,re.I):return False
        if typ=='hand_capacity':return bool(re.search(r'free|room|expand|increase|manage|drop|stor|stow|equip|eat|consume|discard',text,re.I))
        if typ=='container_capacity':return bool(re.search(r'free|empty|remove|discard|inspect|check|another|different|expand|manage|capacity|room',text,re.I))
        if typ=='insufficient_ingredients':
            target=s['candidate_action'].split()[-1]
            return bool(re.search(r'missing|required|necessary|sufficient|recipe',text,re.I) or target.lower() in text.lower())
        if typ in {'missing_workbench','missing_furnace'}:
            if re.search(r"don.t require|does not require|without (?:a |the )?(?:workbench|furnace)|avoid.*(?:workbench|furnace)",text,re.I):return False
            return bool(re.search(r'find|locate|build|construct|access|reach|return|go to|move to|travel|obtain|gather|collect|craft (?:a |the |1 )?(?:workbench|furnace)',text,re.I))
        return True
    explicit=bool(goal!=s['current_goal'] and recovery_text(goal))
    # Restrict inferred intentions to a single sentence mentioning the gap;
    # merely restating the failed action does not establish a recovery plan.
    sentences=re.split(r'(?<=[.!?])\s+',reason)
    support=[t for t in sentences if recovery_text(t)]
    has_intent=bool(support)
    return dict(understanding=understood,structured_recovery_goal=explicit,existing_recovery_goal=goal==s['current_goal'] and recovery_text(goal),reasoning_recovery_intent=has_intent,
        evidence=support,goal=goal,reasoning=reason)

def directed(s,r):
    p=r['decision']['attempts'][-1]['proposal'];v=intent(s,p);action=r['action'];verb=action.split()[0]
    accepted=not extract(r['feedback'])['failed'] and not r['info'].get('step_invalid_action',{}).get(AGENT_ID,False)
    allowed=ACTION_VERBS.get(s['failure_type'],{'enter','inspect','pick','take','equip','unequip','talk','buy','attack','defend','eat','drop','store','craft'})
    direct=accepted and action!=s['candidate_action'] and verb in allowed and (v['structured_recovery_goal'] or v['reasoning_recovery_intent'])
    return dict(step=r['step'],action=action,accepted=accepted,**v,recovery_directed=bool(direct),
        native_feedback=extract(r['feedback'])['feedback'],main_delta=r['reward']['quest'])

def analyze_event(s,continuation,horizon=20):
    rr=continuation[:horizon];items=[directed(s,r) for r in rr];first=items[0] if items else None
    formation=('Recovery objective generated' if first and (first['structured_recovery_goal'] or first['reasoning_recovery_intent']) else
        'Failure acknowledged only' if first and first['understanding'] else 'No recovery' if first else 'Unobserved')
    repairs=[x for x in items if x['recovery_directed']]
    retried=[x for x in items if x['action']==s['candidate_action']]
    successful=[x for x in retried if x['accepted']]
    closed=[x for x in successful if any(y['step']<x['step'] for y in repairs)]
    consecutive=[]
    for a,b in zip(items,items[1:]):
        if a['recovery_directed'] and b['recovery_directed']:consecutive.append([a['step'],b['step']])
    original_goal_returns=[];changed=False
    for x in items:
        if x['goal']!=s['current_goal']:changed=True
        elif changed:original_goal_returns.append(x['step'])
    return dict(id=s['id'],trajectory=s['trajectory'],failure_step=s['step'],failure_type=s['failure_type'],
        current_goal=s['current_goal'],failed_action=s['candidate_action'],public_feedback=s['failure_reason'],
        available_actions=len(rr),window_complete=len(rr)==horizon,understanding_next=first['understanding'] if first else None,
        recovery_class=formation,structured_objective_next=first['structured_recovery_goal'] if first else None,
        reasoning_intent_next=first['reasoning_recovery_intent'] if first else None,
        understanding_within5=any(x['understanding'] for x in items[:5]),formation_within5=any(x['structured_recovery_goal'] or x['reasoning_recovery_intent'] for x in items[:5]),
        execution_any=bool(repairs),execution_steps=[x['step'] for x in repairs],consecutive_execution_pairs=consecutive,
        original_action_retry_steps=[x['step'] for x in retried],original_action_success_steps=[x['step'] for x in successful],
        local_closed_loop_steps=[x['step'] for x in closed],retry_success_scorable=s['failure_type'] not in UNSUPPORTED,
        original_goal_string_return_steps=original_goal_returns,main_gain=sum(x['main_delta'] for x in items),
        repeated_rejection_count=sum(not x['accepted'] for x in retried),next_actions=items,
        source_trajectory=s['source_trajectory'],source_failure_line=s['source_line'],
        caveat='Rule-detected intention and accepted related actions are observable proxies, not proof of a correct plan. No successful retry is unresolved evidence, not proof that a prerequisite was never restored.')

def summarize(events):
    observed=[e for e in events if e['available_actions']];complete=[e for e in events if e['window_complete']]
    scorable=[e for e in complete if e['retry_success_scorable']]
    return dict(events=len(events),post_failure_observed=len(observed),full20=len(complete),right_censored=len(events)-len(complete),
        understanding_next=sum(e['understanding_next'] is True for e in observed),
        structured_objective_next=sum(e['structured_objective_next'] is True for e in observed),
        recovery_classes=dict(Counter(e['recovery_class'] for e in events)),
        formation_next=sum(e['recovery_class']=='Recovery objective generated' for e in observed),
        full20_execution_any=sum(e['execution_any'] for e in complete),
        full20_consecutive_execution=sum(bool(e['consecutive_execution_pairs']) for e in complete),
        full20_successful_retry=sum(bool(e['original_action_success_steps']) for e in scorable),
        full20_closed_local_loop=sum(bool(e['local_closed_loop_steps']) for e in scorable),
        full20_retry_scorable=len(scorable),full20_goal_string_return=sum(bool(e['original_goal_string_return_steps']) for e in complete),
        full20_main_gain_events=sum(e['main_gain']>0 for e in complete))

def main():
    offline();sources={};events=[]
    for s in samples():
        if s['source_trajectory'] not in sources:sources[s['source_trajectory']]=rows(ROOT/s['source_trajectory'])
        rr=[r for r in sources[s['source_trajectory']] if r['step']>s['step']]
        events.append(analyze_event(s,rr))
    gzwrite(RESULTS/'failure_recovery_chains.jsonl.gz',events)
    write(RESULTS/'chain_statistics.json',dict(all=summarize(events),parent=summarize([e for e in events if e['trajectory']=='parent']),
        branches=summarize([e for e in events if e['trajectory']!='parent']),
        by_type={t:summarize([e for e in events if e['failure_type']==t]) for t in sorted({e['failure_type'] for e in events})},
        independent_parent_episodes=1,new_model_calls=0,not_stage27_elicited_answers=True))
    print(json.dumps(read(RESULTS/'chain_statistics.json')['all']),flush=True)

if __name__=='__main__':main()
