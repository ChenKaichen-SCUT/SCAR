"""Content-addressed public evidence; no environment, evaluator or task catalogue."""
import copy
import json
from scar.io import digest
from scar_v3.state import parse_action


def snapshot(controller, obs):
    t=controller.table;step=int(obs['step']);records=[]
    def add(kind,key,value,names,source,observed=None):
        value=copy.deepcopy(value)
        ident='E'+digest([kind,key,value])[:12]
        record=dict(id=ident,kind=kind,key=key,value=value,names=sorted(set(n for n in names if n)),
            source=source,observed_step=step if observed is None else observed,snapshot_step=step)
        assert record['observed_step']<=step
        old=controller.evidence20.get(ident)
        record['first_seen_step']=old['first_seen_step'] if old else step
        controller.evidence20[ident]=copy.deepcopy(record);records.append(record)
    goal=parse_action(controller.target).target
    add('goal',goal,controller.objective,[goal],'user_public_task')
    block=controller.blocker20
    add('blocker',block.get('item',''),block,[block.get('item'),block.get('parent'),goal],'derived_from_public_conditions')
    for group in ('hands','equipment','ground'):
        for name,amount in sorted((t.state.get(group) or {}).items()):
            add('current_object',name,dict(group=group,amount=amount,location=t.state.get('location')),[name],
                'native_current_observation')
    for name,c in sorted(t.containers.items()):
        if t.access(name):
            add('container',name,{k:c.get(k) for k in ('counts','capacity','load','location')},
                [name]+list(c.get('counts') or {}),'native_container_feedback',c.get('step',step))
    for loc,data in sorted(t.places.items()):
        route=t.path(loc)
        if loc==t.state.get('location') or route:
            add('public_location',loc,dict(objects=data['objects'],route=route),
                [loc]+list(data['objects']),'native_observed_map',data.get('step',step))
    for loc in sorted(t.state.get('neighbors') or []):
        add('public_frontier',loc,dict(from_location=t.state.get('location'),route=t.path(loc)),[loc],'native_neighbor_list')
    needed=controller.needed()
    for name,r in sorted(t.recipes.items(),key=lambda pair:(pair[0] not in needed,pair[0])):
        add('recipe',name,r,[name]+r.get('ingredients',[])+r.get('stations',[]),
            'P1_native_public_disclosure',r.get('step',step))
    # Bounded prompt only; full registry is retained for provenance and recovery.
    selected=[];size=0
    for r in records:
        line=json.dumps(r,ensure_ascii=False,separators=(',',':'))
        if len(selected)<64 and size+len(line)+1<=14000:
            selected.append(r);size+=len(line)+1
    controller.request_evidence20=[r['id'] for r in selected]
    return copy.deepcopy(selected)


def check(controller,proposal):
    resolved=[];now=controller.table.state.get('step',0)
    for ident in proposal['evidence_ids']:
        record=controller.evidence20.get(ident)
        if record is None:return 'unknown_evidence_id',[]
        if record['observed_step']>now or record['first_seen_step']>now:return 'future_evidence_id',[]
        resolved.append(record)
    # Mere mention of the final goal doesn't establish an accessible entry.
    supporting=[r for r in resolved if r['kind'] not in ('goal','blocker') and
        proposal['entry'] in r['names']]
    if not supporting:return 'evidence_unrelated_to_execution_entry',resolved
    return None,resolved


def render(controller, obs, memory):
    records=snapshot(controller,obs)
    recovery=dict(state=controller.recovery20,previous_outcomes=controller.acceptance20[-5:],
        lifecycle=controller.lifecycle20[-6:],suspended=controller.suspended20,
        exhausted_entries=controller.entry_attempts20)
    text=('FINAL TASK: '+controller.objective+'\nSPECIFIC BLOCKER: '+json.dumps(controller.blocker20,ensure_ascii=False)+
        '\nCURRENT PUBLIC OBSERVATION:\n'+obs['text']+'\nRECENT PUBLIC TRANSITIONS:\n'+'\n'.join(memory[-3:])+
        '\nPREVIOUS PLANNING / RECOVERY:\n'+json.dumps(recovery,ensure_ascii=False)+
        '\nPUBLIC EVIDENCE (cite IDs):\n'+'\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in records))
    return text,dict(records=copy.deepcopy(records),prompt_characters=len(text),snapshot_step=obs['step'])
