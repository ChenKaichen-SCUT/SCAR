"""Public crafting-game adapter for generic ETBR evidence and blocker records.

Dialogue and task-stage text have no reliable parser in this adapter: UNKNOWN.
The generic interface can accept externally parsed, publicly sourced records.
"""
import copy
from scar_v3.state import parse_action
from .public import public_route


def facts(controller):
    t = controller.table
    records = []
    def add(kind, subject, relation, obj, source, **extra):
        records.append(dict(knowledge_type=kind, subject=subject, relation=relation, object=obj,
            provenance=dict(source=source, public_native_step=t.state.get('step'), **extra)))
    for name, rule in sorted(t.recipes.items()):
        for dep in rule.get('ingredients', []):
            add('production_relation', name, 'requires_material', dep, 'P1_public_recipe', evidence_ids=rule.get('evidence_ids', []))
        for station in rule.get('stations', []):
            add('area_requirement', name, 'requires_area_object', station, 'native_public_required_area_feedback', evidence_ids=rule.get('evidence_ids', []))
    for place, data in sorted(t.places.items()):
        for name, amount in sorted(data['objects'].items()):
            if amount > 0:
                add('source_location', name, 'observed_at', place, 'native_observed_ground', last_observed_step=data.get('step'))
    for place, neighbors in sorted(t.links.items()):
        for dest in sorted(neighbors):
            add('map_connection', place, 'public_neighbor', dest, 'native_public_neighbor_list')
    for edge, guard in sorted(t.guards.items()):
        add('access_condition', edge, 'locked' if guard.get('locked') else 'unlocked',
            guard.get('required') or 'publicly_traversable', 'native_public_enter_feedback')
    return records


def blocker(controller):
    c, t = controller, controller.table
    raw = c.blocker20
    nodes = c.needed() | {raw.get('item'), raw.get('parent')}
    nodes.discard(None)
    # A place is linked only by a publicly observed needed object. An arbitrary
    # new neighbor is not automatically relevant to the current task.
    related = set(nodes)
    for place, data in t.places.items():
        if set(data['objects']) & nodes:
            related.add(place)
            route = public_route(c, place)
            if route: related.update(route)
    goal = parse_action(c.target).target
    return dict(kind=raw.get('kind', 'public_execution_blocked'), subject=raw.get('item', goal),
        parent=raw.get('parent', goal), requires_ground=raw.get('requires_ground', False),
        required_amount=c.amount if raw.get('item',goal)==goal else c.queue_needs.get(raw.get('item'),1),
        public_entities=sorted(related), unresolved=c.ownership(goal)['lower_bound'] < c.amount,
        source='public deterministic execution', public_details=copy.deepcopy(raw))


def unsupported_narrative(text):
    return dict(status='UNKNOWN', reason='no validated dialogue/task-stage parser', text_retained_for_audit=text)

