"""Generic public text extraction. No game names, items, maps or quest rules."""
import re
from scar.io import digest


def extract(obs):
    text=obs['text']
    def match(pattern):
        m=re.search(pattern,text,re.I)
        return m[1].strip().rstrip('.') if m else None
    def counts(value):
        if value is None:return None
        if value.lower() in ('nothing','no objects','none'):return {}
        out={}
        for part in value.split(', '):
            m=re.fullmatch(r'(\d+(?:\.\d+)?) (.+)',part)
            if not m:return None
            out[m[2]]=float(m[1])
        return out
    location=match(r'Current Location: ([^\n]+)')
    hands=counts(match(r'I am holding ([^\n]+)'));equipment=counts(match(r'I have equipped ([^\n]+)'))
    ground=counts(match(r'I see ([^\n]+) near me\.'))
    inventory=counts(match(r'It contains: (.*?) \(capacity:'))
    npcs=match(r'I see ([^\n]+) nearby\.')
    npcs=None if npcs is None else [] if npcs=='no one' else npcs.split(', ')
    m=re.search(r'Current Location:[^\n]*\n(.*?)(?:\nI am holding |\nMy level is |\Z)',text,re.S)
    feedback=(m[1] if m else text).strip()
    # Time, health/stamina/combat tick drift are not novel task information.
    event='\n'.join(line.strip() for line in feedback.splitlines() if line.strip() and not re.search(
        r'^(?:Current Time:|My (?:health|stamina|experience|level|attack|defense) is|I was attacked|I feel tired|I waited for a while|As dawn breaks)',line.strip(),re.I))
    goal=match(r'(?:Required action:|Your (?:task|goal) is|Objective:)\s*([^\n]+)')
    if goal:goal=goal.strip(' `.');
    failed=bool(re.search(r'\b(?:Cannot|Invalid action|not enough|insufficient|do not have|can\x27t|not following the tutorial)\b',feedback,re.I))
    permanent=bool(re.search(r'\b(?:no longer possible|permanently unavailable|impossible to|can never)\b',feedback,re.I))
    features=dict(location=location,hands=hands,equipment=equipment,observed_container_contents=inventory,ground_names=sorted(ground or {}),npcs=sorted(npcs or []),
        neighbors=match(r'Neighboring areas: ([^\n]+)'))
    # Context matches on observed state, not elapsed time or hidden simulation.
    context=dict(features,ground=ground)
    return dict(**features,ground=ground,feedback=feedback,event=event,public_goal=goal,failed=failed,permanent=permanent,
        signature=digest(features),context=digest(context),entities=sorted(set(ground or {})|set(hands or {})|set(equipment or {})|set(npcs or [])))


def satisfied_literal(goal,state):
    # Public destination comparison only. No map graph, path, key or NPC rule.
    m=re.fullmatch(r'enter\s+(.+)',goal or '')
    return bool(m and state['location'] and state['location'].split(',')[-1].strip()==m[1].strip('"\''))
