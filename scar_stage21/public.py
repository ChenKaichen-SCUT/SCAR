"""Typed entry validation uses PUBLIC controller state only.

No world, task recipe catalogue, native valid-action list or other algorithm's
trajectory enters enumeration or prioritization. UNKNOWN remains distinct.
"""
import copy
from collections import deque
from scar.io import digest
from scar_sequence.planner import q
from scar_v3.state import parse_action


def public_route(c,destination):
    """Public BFS excluding disclosed locked edges without a held key."""
    t=c.table;start=t.state['location'];todo=deque([(start,[])]);seen={start}
    key=(t.state.get('hands') or {}).get('key',0)>0
    while todo:
        node,path=todo.popleft()
        if node==destination:return path
        for nxt in t.links.get(node,[]):
            guard=t.guards.get(node+'->'+nxt,{})
            if nxt not in seen and not (guard.get('locked') and not key):
                seen.add(nxt);todo.append((nxt,path+[nxt]))
    return None


def access(c,name):
    t=c.table;loc=t.state['location']
    if name==loc:return dict(accessible=True,mode='current_location',route=[],first_action=None)
    if name=='inventory' and t.inventory:return dict(accessible=True,mode='carried_inventory',route=[],first_action='inspect inventory')
    if name in c.visible():return dict(accessible=True,mode='current_public_object',route=[],first_action='inspect '+q(name))
    if name in t.places or name in {x for ns in t.links.values() for x in ns}:
        path=public_route(c,name)
        return dict(accessible=bool(path),mode='public_location_route',route=path,first_action='enter '+q(path[0]) if path else None)
    for place,data in sorted(t.places.items()):
        if data['objects'].get(name,0)>0 and (path:=public_route(c,place)):
            return dict(accessible=True,mode='historically_observed_object_route',route=path,first_action='enter '+q(path[0]),destination=place,contents_currently_confirmed=False)
    return dict(accessible=False,mode='no_current_public_access_or_unblocked_route',route=None,first_action=None)


def fields_support(record,name):
    """Only typed entity-bearing fields; never search arbitrary free-text claims."""
    if record['kind']=='goal':return []
    out=[];value=record['value']
    if record['kind']=='blocker':
        entries=value.get('public_entries',{})
        if name in entries.get('reachable',[]):out.append('public_entries.reachable')
        if name in entries.get('visible',[]):out.append('public_entries.visible')
        if name in entries.get('observed_locations',{}):out.append('public_entries.observed_locations')
        return out
    if name in record['names']:out.append('names')
    if record['kind'] in ('public_frontier','public_location'):
        if record['key']==name:out.append('location_key')
        if value.get('from_location')==name:out.append('from_location')
        if name in (value.get('route') or []):out.append('route')
        if name in value.get('objects',{}):out.append('observed_objects')
    if record['kind']=='current_object' and value.get('location')==name:out.append('object_location')
    if record['kind']=='container':
        if value.get('location')==name:out.append('container_location')
        if name in (value.get('counts') or {}):out.append('container_counts')
    return out


def shadow(c,proposal):
    refs=[];now=c.table.state['step']
    for ident in proposal['evidence_ids']:
        rec=c.evidence20.get(ident)
        if rec is None:return dict(category='III',reason='unknown_ID',structural_accept=False,hypothesis_accept=False)
        if rec['observed_step']>now or rec['first_seen_step']>now or rec['snapshot_step']>now:
            return dict(category='III',reason='future_ID',structural_accept=False,hypothesis_accept=False)
        refs.append(rec)
    entry=access(c,proposal['entry']);target=access(c,proposal['target'])
    named=set(c.needed())|set(c.table.recipes)|set(c.visible())|set(c.table.places)
    for ns in c.table.links.values():named.update(ns)
    for d in c.table.places.values():named.update(d['objects'])
    for r in c.table.recipes.values():named.update(r.get('ingredients',[])+r.get('stations',[]))
    invalid=[]
    if not entry['accessible']:invalid.append('entry_not_publicly_accessible')
    if proposal['target'] not in named:invalid.append('target_not_publicly_named')
    kind=proposal['type'];candidate=entry['first_action']
    if kind=='EXPLORE_FRONTIER':
        candidate=target['first_action']
        if target['mode'] not in ('current_location','public_location_route') or not target['accessible']:
            invalid.append('exploration_destination_not_accessible_public_location')
        elif target['mode']=='current_location':invalid.append('destination_already_reached')
    if kind=='INSPECT_OBJECT':
        candidate=target['first_action']
        if not target['accessible']:invalid.append('inspection_target_not_accessible')
        if proposal['target'] in c.table.inspected:invalid.append('already_inspected')
    if kind=='CRAFT_PRECONDITION' and not c.table.recipes.get(proposal['target'],{}).get('ingredients'):
        invalid.append('craft_recipe_unpublished')
    unproven_dependency=kind in ('ACQUIRE_MATERIAL','LOCATE_PRECONDITION','CRAFT_PRECONDITION') and proposal['target'] not in c.needed()|{c.blocker20.get('item')}
    if kind=='LOCATE_PRECONDITION':
        if target['mode'] in ('current_location','public_location_route'):
            invalid.append('LOCATE_object_type_used_for_location_not_unresolved_prerequisite')
        elif c._known_path(proposal['target']):invalid.append('LOCATE_public_path_already_known')
    if candidate and c.assess(candidate)['status']=='REJECT':invalid.append('first_action_known_condition_reject')
    paths=[dict(id=r['id'],entry_fields=fields_support(r,proposal['entry']),target_fields=fields_support(r,proposal['target'])) for r in refs]
    direct=any(r['entry_fields'] for r in paths)
    target_supported=any(r['target_fields'] for r in paths)
    # This diagnoses public evidence scope, not novelty, remaining budget, risk
    # or whole-intent feasibility. A separate field preserves those limits.
    if invalid:category='III';reason=';'.join(invalid)
    elif unproven_dependency and target_supported:category='II';reason='bounded_public_material_hypothesis_not_yet_in_proven_dependency_closure'
    elif direct:category='I';reason='typed_cited_public_fields_support_accessible_entry'
    elif target_supported:category='II';reason='public_accessible_entry_and_supported_target_but_relation_hypothetical'
    else:category='IV';reason='insufficient_linked_public_reference'
    return dict(category=category,reason=reason,structural_accept=category=='I',hypothesis_accept=category in ('I','II'),
        entry_access=entry,target_access=target,first_action=candidate,field_relations=paths,
        target_dependency_unproven=unproven_dependency,
        inherited_exploration_exhausted=c.exploration_spent>=18,causal_target_entry_relation_proven=False,
        action_outcome='UNKNOWN until native branch',bounded_hypothesis_scope=True)
