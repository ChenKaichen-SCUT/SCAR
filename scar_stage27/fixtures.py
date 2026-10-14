"""Compile static diagnostic fixtures from public text, with quote provenance.

This is offline dataset preparation, not a state layer available to any Agent.
No environment internals or quest evaluator state may enter this module.
"""
import json
import re
from agents.agc.state import extract
from scar_stage26.source_audit import subtype
from .common import UNDERSTANDING_SYSTEM,GROUNDING_HEADER

def failure_type(feedback):
    s=subtype(feedback)
    if s!='other_public_failure':return s
    text=feedback.lower()
    pairs=[('not held in hand','target_not_held'),("no path to",'no_path'),
        ("container can't be stored",'container_nesting'),('already have','equipment_slot_occupied'),
        ('not a writable object','not_writable'),('no such object','unknown_object'),
        ('necessary furnace','missing_furnace'),('no way to craft','not_craftable'),
        ('not edible','not_edible'),('not found in','object_unavailable'),
        ('cannot find','object_unavailable')]
    for phrase,label in pairs:
        if phrase in text:return label
    return 'unspecified_rejection'

def public_failure_line(obs):
    return '\n'.join(line for line in extract(obs)['feedback'].splitlines()
                     if re.search(r'\b(?:Cannot|Invalid action|not enough|insufficient|do not have|can.t|not following the tutorial)\b',line,re.I))

def compile_state(prefix):
    current=extract(prefix[-1]['feedback']);requirements={};tools={};failed=[];containers={}
    for r in prefix:
        for timing,obs in [('before',r['observation']),('after',r['feedback'])]:
            e=extract(obs)
            if e['observed_container_contents'] is not None:
                containers[r['action'] if timing=='after' else 'observation']=dict(
                    contents=e['observed_container_contents'],step=r['step'],timing=timing,
                    quote=e['feedback'],current_contents_unknown=True)
            for line in obs['text'].splitlines():
                if re.search(r'\b(?:tool|tools|workbench|furnace)\b',line,re.I):
                    tools[line]=dict(quote=line,step=r['step'],timing=timing,location=e['location'],historical=True)
        e=extract(r['feedback'])
        if e['failed']:
            quote=public_failure_line(r['feedback'])
            entry=dict(action=r['action'],step=r['step'],quote=quote,location=e['location'],historical=True)
            failed.append(entry);requirements[quote]=entry
    last=prefix[-1]
    return dict(inventory=dict(hands=current['hands'],equipped=current['equipment'],
                    container_last_observations=list(containers.values()),step=last['step']),
        known_tools=list(tools.values()),known_requirements=list(requirements.values()),
        failed_actions=failed,blocked_actions=[dict(action=last['action'],quote=public_failure_line(last['feedback']),
            scope='Rejected in the last transition; continued blocking is not established.')]
            if current['failed'] else [],current_location=current['location'],
        provenance_policy='Every quote comes from a public before/after observation at or before this checkpoint. No hidden rules. Historical records are not current inventory.')

def make_messages(sample,condition,original=None,state=None):
    if condition=='understanding':
        data={k:sample[k] for k in ['step','current_goal','observation','inventory','location','previous_actions','candidate_action','environment_response','post_failure_observation']}
        return [dict(role='system',content=UNDERSTANDING_SYSTEM),dict(role='user',content=json.dumps(data,ensure_ascii=False))]
    messages=[dict(x) for x in (original or sample['original_messages'])]
    if condition=='B':
        messages[-1]['content']+=GROUNDING_HEADER+json.dumps(state or sample['grounded_state'],ensure_ascii=False)
    return messages

def provenance_check(state,prefix):
    obs={(r['step'],t):r[k]['text'] for r in prefix for t,k in [('before','observation'),('after','feedback')]}
    for f in state['known_tools']:
        assert f['quote'] in obs[f['step'],f['timing']]
    for f in state['known_requirements']+state['failed_actions']:
        assert f['quote'] and f['quote'] in obs[f['step'],'after']
    assert all(f['step']<=prefix[-1]['step'] for f in state['failed_actions'])
