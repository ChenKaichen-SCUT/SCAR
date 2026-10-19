"""Projection for model input. Full ledger/evidence remains in local audit files."""
import json

def short_refs(value):
    if isinstance(value,dict):
        if isinstance(value.get('quote'),str) and isinstance(value.get('step'),int):return {'observation_step':value['step']}
        return {k:short_refs(v) for k,v in value.items() if k not in {'reasoning','evidence_steps','trials'}}
    if isinstance(value,list):return [short_refs(v) for v in value]
    return value

def packet_for(s,max_chars=6000):
    """Never truncate the raw full history; select only a bounded decision projection."""
    tasks=[t for t in s.tasks.values() if t['status']=='open']
    tasks.sort(key=lambda t:(t['id']!=s.focus,{'tutorial':0,'main':1,'unspecified':2,'side':3}.get(t['scope'],4)))
    task_ids={t['id'] for t in tasks[:3]};objective=s.objective
    if objective:task_ids.add(objective.get('goal_id'))
    bindings={bid for tid in task_ids for bid in s.tasks.get(tid,{}).get('bindings',[])}
    p={'step':s.step,'location':s.location,'visible':s.visibility,'hands':s.hands,'equipped':s.equipped,
       'inventory_currently_observed':s.hands_observed,'nearby':s.nearby,'neighbors':s.neighbors,
       'tasks':[{'id':t['id'],'text':t['text'],'scope':t['scope']} for t in tasks[:3]],
       'objective':{k:objective[k] for k in ['action','goal_id','status']} if objective else None,
       'task_parameters':[{'value':s.literals[b]['value'],'observation_step':s.literals[b]['evidence']['step']} for b in sorted(bindings) if b in s.literals],
       'repeat_control':s.repeat_status(),
       'missing_fields':'Other observations, recipes and task evidence remain in the full history; omission here does not mean absence.'}
    totals,unknown=s.accessible()
    optional=[('known_accessible_quantities',totals),('inventory_uncertainties',unknown),
        ('carried_containers',short_refs({k:v for k,v in s.containers.items() if k in s.hands or k in s.equipped})),
        ('observed_container_capacity',short_refs(s.container_limits))]
    if objective:
        need=s.dependency_requirements(objective['action']);targets=set(need)
        parts=objective['action'].split()
        if parts:targets.add(parts[-1])
        optional += [('deficits',s.deficit_vector(objective['action'])),('relevant_recipes',[short_refs(s.recipes[k]) for k in sorted(targets) if k in s.recipes])]
    optional += [('queue',s.queue[:3]),('next_preparation',s.preparation()),('conditional_hand_refusal',short_refs(s.hand_limit)),
        ('negative_capabilities',short_refs(s.negative_capabilities)),('last_dispatch',short_refs(s.interventions[-1]) if s.interventions else None)]
    if s.test_specs:optional.append(('latest_test',short_refs(list(s.test_specs.values())[-1])))
    omitted=[]
    for key,value in optional:
        candidate={**p,key:value}
        if len(json.dumps(candidate,ensure_ascii=False,separators=(',',':')))<=max_chars-300:p=candidate
        else:omitted.append(key)
    p['omitted_projection_fields']=omitted
    # Extremely large task or scene lists are omitted explicitly, never clipped into misleading facts.
    for key in ['nearby','tasks','task_parameters']:
        if len(json.dumps(p,ensure_ascii=False,separators=(',',':')))<=max_chars:break
        p.pop(key,None);p['omitted_projection_fields'].append(key+' (read full observation/history)')
    if len(json.dumps(p,ensure_ascii=False,separators=(',',':')))>max_chars:raise ValueError('Decision projection exceeds bound; refuse to silently truncate')
    return p
