"""Conditional memory of native public feedback. No engine or task lookup.

Anonymous carrying feedback identifies a STATE, not a universal hazardous item.
An item association needs acquisition evidence, and discard/cessation strengthens
it. Enemy damage alone never creates a carrying constraint.
"""
import copy
import re
from scar.agents.scar.state import feedback_text
from scar_v3.state import parse_action
from .acquisition import requested


def health(obs):
    m = re.search(r'My health is at ([\d.]+)', obs.get('text', ''))
    return float(m[1]) if m else None


def public_frame(controller):
    t = controller.table
    names = set(t.state.get('hands') or {}) | set(t.state.get('equipment') or {})
    for n, c in t.containers.items():
        if t.carried(n):
            names.update(c.get('counts') or {})
    return dict(location=t.state.get('location'), equipment=copy.deepcopy(t.state.get('equipment')),
        hands=copy.deepcopy(t.state.get('hands')), owned={n: controller.ownership(n) for n in sorted(names)},
        containers={n: copy.deepcopy(c) for n, c in t.containers.items() if t.access(n)},
        step=t.state.get('step'))


def acquired(action, feedback, before):
    p = parse_action(action)
    match = re.search(r'I stored ([\d.]+) ', feedback)
    if p.verb == 'store' and match:
        transferred = float(match[1])
        # Only an equipped/carried destination adds to owned material.
        if p.args[-1] != 'inventory' and p.args[-1] not in (before.get('equipment') or {}) and p.args[-1] not in (before.get('hands') or {}):
            return 0, transferred
        return max(0, transferred-(before.get('hands') or {}).get(p.target, 0)), transferred
    if p.verb == 'pick up' and re.search(r'I picked up ', feedback):
        return 1, 1
    if p.verb == 'take out' and re.search(r'I took out ', feedback):
        c = p.args[-1]
        return (0 if c == 'inventory' or c in (before.get('equipment') or {}) or c in (before.get('hands') or {}) else 1), 1
    return 0, 0


class ConsequenceMemory:
    def __init__(self):
        self.records = []
        self.last_carry = None
        self.discards = []

    def observe(self, before, action, after, frame_before, frame_after):
        p = parse_action(action)
        fb = feedback_text(after.get('text', ''))
        hp0, hp1 = health(before), health(after)
        delta = hp0-hp1 if hp0 is not None and hp1 is not None else None
        gain, moved = acquired(action, fb, frame_before)
        # Generic textual consequence patterns. Numeric threshold is extracted
        # from current native feedback, never a baked-in material/game rule.
        drain = re.search(r'draining ([\d.]+) HP', fb, re.I)
        carrying = bool(drain and re.search(r'carrying|carry|carried', fb, re.I))
        count = re.search(r'energy of ([\d.]+) [^\n]*?objects', fb, re.I)
        threshold = re.search(r'carrying more than ([\d.]+) ', fb, re.I)
        record = dict(id=f'consequence:{after.get("step")}:{len(self.records)}', step=after.get('step'),
            action=action, verb=p.verb, item=p.target, requested=requested(action),
            actual_acquired=gain, actual_transferred=moved, before=frame_before, after=frame_after,
            health_before=hp0, health_after=hp1, health_loss=delta, feedback=fb,
            explicit_carrying_damage=float(drain[1]) if carrying else 0,
            certainty='direct_public_carrying_state' if carrying else 'temporal_association' if delta and delta > 0 else 'no_observed_loss',
            confounders='simultaneous environment/NPC effects are not excluded',
            risk_item=None, item_attribution='UNKNOWN', cessation_evidence=None,
            threshold=float(threshold[1]) if threshold else None,
            observed_affected_count=float(count[1]) if count else None,
            invalidation=['quantity changes', 'location changes', 'equipment changes', 'new contradictory feedback'])
        if carrying:
            affected = record['observed_affected_count']
            # A one-material increase matching the explicitly affected count
            # supports a conditional hypothesis, not an intrinsic item property.
            if gain > 0 and affected is not None and gain + frame_before['owned'].get(p.target, {}).get('lower_bound', 0) == affected:
                record.update(risk_item=p.target, item_attribution='single_acquisition_matches_public_affected_count')
            elif self.last_carry and self.last_carry.get('risk_item'):
                item = self.last_carry['risk_item']
                own = frame_after['owned'].get(item, {}).get('lower_bound')
                if own is not None and own == affected:
                    record.update(risk_item=item, item_attribution=self.last_carry['item_attribution'])
            self.last_carry = copy.deepcopy(record)
        removed = p.verb in ('discard', 'drop') and bool(re.search(r'I discarded |I dropped ', fb))
        if removed:
            previous = self.last_carry
            resolved = bool(previous and not carrying and previous['after']['location'] == frame_before['location']
                and previous['after']['equipment'] == frame_before['equipment']
                and previous.get('risk_item') == p.target)
            discard = dict(step=after.get('step'), item=p.target, action=action, feedback=fb,
                risk_related=resolved, risk_evidence=previous['id'] if resolved else None)
            self.discards.append(discard)
            if resolved:
                # Store an evidence pair anchored at this location/equipment.
                strengthened = copy.deepcopy(previous)
                strengthened.update(id=record['id']+':cessation',
                    item_attribution='carrying_feedback_plus_discard_cessation',
                    cessation_evidence=discard)
                self.records.append(strengthened)
                record['cessation_evidence'] = discard
            if not carrying:
                self.last_carry = None
        if carrying or (delta is not None and delta > 0) or gain or removed:
            self.records.append(copy.deepcopy(record))
        return record

    def check(self, controller, action):
        p, t = parse_action(action or ''), controller.table
        frame = public_frame(controller)
        own = controller.ownership(p.target)['lower_bound']
        n = requested(action) or 0
        held = (frame['hands'] or {}).get(p.target, 0)
        is_acquisition = p.verb == 'pick up' or (p.verb == 'store' and p.args[-1] == 'inventory') or p.verb == 'take out'
        added = max(0, n-held) if p.verb == 'store' else 1
        if p.verb == 'take out' and (p.args[-1] == 'inventory' or t.carried(p.args[-1])):
            added = 0
        matches = []
        for r in self.records:
            if not r.get('risk_item') or r['risk_item'] != p.target:
                continue
            same = r['after']['location'] == frame['location'] and r['after']['equipment'] == frame['equipment']
            total = own+added
            threshold = r.get('threshold')
            prior_count = r.get('observed_affected_count')
            repeated = same and prior_count is not None and total >= prior_count
            threshold_scope = same and r.get('cessation_evidence') and threshold is not None and total > threshold
            matches.append(dict(evidence_id=r['id'], same_location_equipment=same,
                predicted_carried_public_lower_bound=total, observed_affected_count=prior_count,
                threshold=threshold, item_attribution=r['item_attribution'],
                repeats_supported_harm=bool(is_acquisition and added > 0 and (repeated or threshold_scope)),
                conditional_trial=not (repeated or threshold_scope)))
        reject = any(m['repeats_supported_harm'] for m in matches)
        return dict(status='REJECT' if reject else 'UNKNOWN', evidence=matches[-12:],
            reason='repeat_observed_harmful_carrying_configuration' if reject else 'changed_or_unobserved_conditions_allow_trial',
            permanent_item_ban=False)

    def to_dict(self):
        return copy.deepcopy(self.__dict__)

    @classmethod
    def from_dict(cls, data):
        obj = cls(); obj.__dict__.update(copy.deepcopy(data)); return obj
