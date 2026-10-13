"""Bound acquisition, never crafting batches, using public accounting only."""
import math
from scar_sequence.planner import q
from scar_v3.state import parse_action
from .config import UNKNOWN_ACQUISITION


def requested(action):
    p = parse_action(action)
    try:
        return int(p.args[0]) if p.verb in ('store', 'discard', 'craft') else 1
    except (ValueError, IndexError):
        return None


def public_demand(controller, item, hint=None):
    """Immediate nominal requirement, not multiplied by requested craft batch.

    A FIFO hint is bounded trial demand unless backed by an attested recipe.
    Historical remote supply is deliberately absent from ownership.
    """
    goal = parse_action(controller.target).target
    if item == goal:
        return controller.amount, 'public_goal_possession', []
    values, sources = [], []
    for parent in controller._all_needed(goal) | set(controller.queue):
        rule = controller.table.recipes.get(parent, {})
        value = (rule.get('quantities') or {}).get(item)
        if value is not None and (controller.table.count(parent) or 0) < controller.queue_needs.get(parent, 1):
            values.append(value)
            sources.append({'product': parent, 'nominal_quantity': value,
                            'evidence_ids': rule.get('evidence_ids', [])})
    if values:
        return max(values), 'known_immediate_nominal_requirement_not_batch_consumption', sources
    return None, 'UNKNOWN_bounded_trial', []


def bound_store(controller, action, *, hint=None, ground_need=None, source='S1'):
    p, t = parse_action(action), controller.table
    if p.verb != 'store' or not p.args or p.args[-1] != 'inventory':
        return action, None
    old = requested(action)
    if old is None or old <= 0:
        return action, None
    held = (t.state.get('hands') or {}).get(p.target, 0)
    ground = (t.state.get('ground') or {}).get(p.target, 0)
    own = controller.ownership(p.target)
    demand, certainty, evidence = public_demand(controller, p.target, hint)
    if ground_need is not None:
        # P3 already computed the immediate deficit. Include held copies that
        # native store moves first; do not shrink store 2 to store 1.
        deficit = max(0, ground_need)
        certainty = 'P3_immediate_public_deficit'
    elif demand is not None:
        deficit = max(0, demand-own['lower_bound'])
    else:
        deficit = UNKNOWN_ACQUISITION
    fresh = min(ground, math.ceil(deficit))
    count = min(old, int(held + fresh))
    # A redundant ground-only acquisition is not a valid zero-count action.
    bounded = f'store {count} {q(p.target)} inventory' if count > 0 else None
    return bounded, dict(source=source, item=p.target, demand=demand, demand_status=certainty,
        fifo_hint=hint, held=held, owned=own, ground=ground,
        new_ground_deficit=deficit, original_quantity=old, selected_quantity=count,
        expected_new_ground=max(0, count-held), original_action=action, bounded_action=bounded,
        evidence=evidence,
        reason='held_first_plus_public_deficit' if count != old else 'already_within_demand',
        capacity_and_external_mutations='UNKNOWN; actual transfer recorded after execution')
