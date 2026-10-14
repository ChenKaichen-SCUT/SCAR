"""Public operational metrics, separate from native outcome verification."""
import re
from collections import Counter
from agents.agc.state import extract
from agents.rec_v1.state import Tracker,failed,visible
from .common import *

def source(seed,method):
    return baseline(seed) if seed==42 and method=='AGC-v2' else RESULTS/'runs'/case_id(seed,method)

def goal(row):return row['decision']['attempts'][-1]['proposal'].get('goal_description','')

def rejected(row):return failed(row['feedback']) or bool(row.get('invalid_action',row['info'].get('step_invalid_action',{}).get(AGENT_ID,False)))

def categories(feedback):
    text=extract(feedback)['feedback'];out=[]
    for key,pattern in [('capacity',r'not enough space|capacity|hands? (?:is |are )?full|inventory.*full'),
                        ('materials',r'ingredients|insufficient.*(?:amount|material)|sufficient amount'),
                        ('facility',r'Missing necessary .+ in the current area|workbench|workstation'),
                        ('tools',r'\btools?\b'),
                        ('unavailable_object',r'no such|not found|not holding|not in .+|do not have|cannot find'),
                        ('visibility',r'too dark|cannot see'),
                        ('action_format',r'Invalid action|format|syntax')]:
        if re.search(pattern,text,re.I):out.append(key)
    return out or ['other_public_rejection']

def audit(rr):
    tracker=Tracker();pending={};last_conditions={};drops={};seen_states=set();seen_areas=set();out=[];recoveries=[]
    if rr:
        b=extract(rr[0]['observation']);seen_states.add(b['signature']);seen_areas.add(b['location'])
    for row in rr:
        n=row['step'];b=extract(row['observation']);a=extract(row['feedback']);act=row['action'];bad=rejected(row);g=goal(row)
        tracker.ingest(row['observation']);assessment=tracker.assess(dict(action=act,goal_description=g))
        key=(b['location'],act);repeat=bad and key in pending;cats=categories(row['feedback']) if bad else []
        preconditions={'capacity','materials','facility','tools','unavailable_object','visibility'}
        repeated_conditions=[c for c in cats if c in preconditions and (*key,c) in last_conditions]
        recovery=None
        if bad:
            if key not in pending:pending[key]=dict(first_failure=n,last_failure=n,count=1)
            else:pending[key].update(last_failure=n,count=pending[key]['count']+1)
            for c in cats:last_conditions[*key,c]=n
        else:
            if key in pending:
                recovery=dict(location=b['location'],action=act,**pending.pop(key),success_step=n)
                recovery.update(delay=n-recovery['first_failure'],within20=n-recovery['first_failure']<=20);recoveries.append(recovery)
            for k in list(last_conditions):
                if k[:2]==key:del last_conditions[k]
        moved=re.fullmatch(r'(drop) (\S+)|(discard) (\d+(?:\.\d+)?) (\S+) (\S+)',act)
        reacquire=re.fullmatch(r'pick up (\S+)|take out (\S+) (\S+)',act)
        pickup=None
        if not bad and moved:drops[b['location'],moved[2] or moved[5]]=n
        if not bad and reacquire:
            item=reacquire[1] or reacquire[2];last=drops.pop((b['location'],item),None)
            if last is not None:pickup=dict(item=item,removed_step=last,reacquired_step=n,delay=n-last)
        darkness=visible(row['observation']) and not visible(row['feedback']) and 'too dark to see' in row['feedback']['text'].lower()
        removal_darkness=bool(darkness and re.match(r'^(?:drop|store|unequip) ',act))
        out.append(dict(step=n,action=act,goal=g,location=b['location'],public_rejected=bad,rejection_categories=cats,
            repeated_failure=repeat,repeated_missing_conditions=repeated_conditions,recovery=recovery,reacquisition=pickup,
            visibility_lost=darkness,removal_visibility_lost=removal_darkness,
            shadow_assessment=assessment,known_recipe_count=len(tracker.recipes),
            native_invalid=bool(row.get('invalid_action',row['info'].get('step_invalid_action',{}).get(AGENT_ID,False))),
            new_public_signature=a['signature'] not in seen_states,new_area=a['location'] not in seen_areas,
            quest_gain=row['reward']['quest'],quest_total=row['scores']['quest'],
            chapter1=bool((row.get('main_quest_progress') or {}).get('chapter',0)>=1),
            full_complete=bool((row.get('main_quest_progress') or {}).get('complete'))))
        tracker.observe(row['observation'],act,row['feedback'],g);seen_states.add(a['signature']);seen_areas.add(a['location'])
    return out,recoveries

def totals(rows_):
    c=Counter()
    for x in rows_:
        c['actions']+=1;c['public_rejected']+=x['public_rejected'];c['native_invalid']+=x['native_invalid'];c['wait']+=x['action']=='wait'
        c['repeated_failure']+=x['repeated_failure'];c['repeated_missing_conditions']+=bool(x['repeated_missing_conditions'])
        c['reacquisition_cycles']+=x['reacquisition'] is not None;c['visibility_lost']+=x['visibility_lost'];c['removal_visibility_lost']+=x['removal_visibility_lost']
        c['recoveries']+=x['recovery'] is not None;c['recoveries20']+=bool(x['recovery'] and x['recovery']['within20'])
        c['new_public_signatures']+=x['new_public_signature'];c['new_areas']+=x['new_area'];c['quest_gain']+=x['quest_gain']
        for cat in x['rejection_categories']:c['rejection_'+cat]+=1
        for reason in x['shadow_assessment']['reasons']:c['shadow_'+reason['kind']]+=1
    c['main_final']=rows_[-1]['quest_total'] if rows_ else 0;c['chapter1']=int(any(x['chapter1'] for x in rows_));c['full_complete']=int(any(x['full_complete'] for x in rows_))
    c['accepted']=c['actions']-c['public_rejected']
    return dict(c)
