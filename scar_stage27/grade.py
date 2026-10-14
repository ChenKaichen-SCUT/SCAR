"""Transparent public-feedback rubric; no model judge or hidden game knowledge.

Rules score explicit rejection recognition, not correctness of every speculative
sentence. Public-evidence manual adjudications override the lexical screen.
"""
import re
from collections import Counter
from .common import *

RUBRIC={
 'hand_capacity':(r'hand|inventory|carry',r'full|space|capacity|occup',r'free|drop|stor|stow|equip|capacity|space'),
 'container_capacity':(r'satchel|bag|container',r'full|space|capacity|remain',r'free|empty|discard|remove|space|capacity|another container'),
 'locked_exit':(r'lock',r'door|path|enter|entry|exit',r'key|unlock|lockpick|access|alternate'),
 'missing_lockpick_tool':(r'lockpick|lock.?pick',r'tool|hand|held|holding',r'obtain|hold|held|hand|acquire|key|unlock'),
 'missing_writing_tool':(r'writ|pen',r'tool|hand|held|holding',r'hold|held|hand|pen|obtain|acquire'),
 'missing_workbench':(r'workbench',r'missing|lack|no |not |absen|requir',r'workbench'),
 'missing_furnace':(r'furnace',r'missing|lack|no |not |absen|requir',r'furnace'),
 'combat_blocks_exit':(r'block|prevent|obstruct',r'exit|escape|path|movement|leav|enter',r'defeat|fight|combat|attack|remov|clear|bypass|neutral|unblock|threat|surviv'),
 'not_equippable':(r'equip',r'not |cannot|can.t|lack|reject',r'equippable|equip|different|other'),
 'object_not_held_or_visible':(r'hand|held|present|access|found|target|inspect|locat',r'not|no |lack|could not|cannot|unavail|absen',r'hand|pick|obtain|locat|find|access|target|inspect|information|light'),
 'insufficient_ingredients':(r'ingredient|material|resource',r'insufficient|not |lack|missing|enough|does not',r'ingredient|recipe|material|quantit|amount'),
 'target_not_held':(r'hand|held|holding',r'not |no |lack|only|must|requir',r'hold|held|hand|pick'),
 'no_path':(r'path|route|adjacen|connect|neighbor',r'no |not |unavail|lack|non|doesn.t',r'path|route|adjacen|neighbor|map|navigate|return'),
 'container_nesting':(r'container|bag|satchel',r'nest|inside|another|within|other container',r'not|cannot|separate|alternative|drop|equip|non.container|invalid'),
 'equipment_slot_occupied':(r'equip|slot|container',r'already|occup|one |single|another',r'unequip|replace|swap|remove|free|slot'),
 'not_writable':(r'writ|surface',r'not |cannot|can.t|tool|invalid',r'writable|surface|paper|target'),
 'unknown_object':(r'object|item|note|weapon|dagger',r'not |no |non.exist|unrecogn|unknown|doesn.t|does not',r'exist|valid|recogn|find|identify|known|name|actual|writable'),
 'object_unavailable':(r'object|item|target|container|npc|paper|workbench|hall|thread|bread|bag|satchel|lyra|goblin',r'not |no |unavail|cannot|can.t|invalid|unrecogn|missing',r'locat|present|find|valid|target|exist|check|inventory|container|available'),
 'not_craftable':(r'craft|recipe',r'not |no |cannot|can.t|lack|does not|uncraft',r'craft|acquir|gather|find|obtain|alternative'),
 'not_edible':(r'edible|eat|food',r'not |cannot|can.t',r'edible|food|eat|heal|alternative'),
 'unspecified_rejection':(r'lockpick|lock.?pick|reject|fail',r'unknown|not specify|not establish|does not|unspecified|unclear|no explicit',r'unknown|check|inspect|information|key|tool|unclear'),
}

def grade(s,answer):
    if not isinstance(answer,dict) or not any(answer.get(k) for k in ['failure_reason','missing_preconditions','next_priority']):
        return dict(label='No grounding',cause_correct=False,recovery_condition_correct=False,reviewer='public_rule_screen',note='没有可解析的诊断回答。')
    reason=str(answer.get('failure_reason',''));missing=str(answer.get('missing_preconditions',''));priority=str(answer.get('next_priority',''))
    p,q,r=RUBRIC[s['failure_type']]
    cause=bool(re.search(p,reason,re.I) and re.search(q,reason,re.I))
    recovery=bool(re.search(r,missing,re.I) and re.search(r,priority,re.I))
    label='Correct grounding' if cause and recovery else 'Partial grounding' if cause else 'Wrong grounding'
    return dict(label=label,cause_correct=cause,recovery_condition_correct=recovery,reviewer='public_rule_screen',
        evidence=dict(reason=reason,missing=missing,priority=priority),
        note='公开拒绝类别的原因词及对应条件/恢复方向核验；非整段自由文本的逻辑证明。',
        matched_patterns=[p,q,r])

def main():
    old=read(RESULTS/'understanding_adjudications.json') if (RESULTS/'understanding_adjudications.json').exists() else {}
    result={}
    for s in samples():
        p=RESULTS/'probes'/s['id']/'understanding/result.json'
        if not p.exists():continue
        answer=read(p)['answer'];j=grade(s,answer)
        if s['id'] in old and old[s['id']]['reviewer']!='public_rule_screen':
            j=dict(old[s['id']],rule_screen=j)
        result[s['id']]=j
    write(RESULTS/'understanding_judgments.json',result)
    print(dict(Counter(j['label'] for j in result.values())))

if __name__=='__main__':main()
