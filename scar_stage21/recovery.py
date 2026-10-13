"""ETBR generic task-evidence interface. No recipes, game names or native engine.

Adapters supply typed PUBLIC facts and a blocker with publicly linked entities.
Unparsed dialogue and narrative stages remain UNKNOWN, not invented facts.
"""
import copy
from scar.io import digest
from .config import EXTRA_CREDITS, CREDITS_PER_BLOCKER, MAX_TRANSIT_STEPS, MAX_ACTIONS

SUPPORTED_TYPES = frozenset(('production_relation', 'source_location', 'area_requirement',
    'map_connection', 'access_condition', 'task_condition', 'task_stage'))


def blocker_id(blocker):
    return 'B' + digest({k: blocker.get(k) for k in ('kind', 'subject', 'parent', 'requires_ground')})[:16]


class Recovery:
    def __init__(self):
        self.seen = {}
        self.deltas = []
        self.consumed = []
        self.grants = []
        self.events = []
        self.last_check = {}

    def ingest(self, facts, action, step, *, initial=False):
        """Content identity excludes timestamps and action; repeated facts stay old."""
        new = []
        for fact in facts:
            kind = fact['knowledge_type']
            if kind not in SUPPORTED_TYPES:
                continue
            key = digest([kind, fact['subject'], fact['relation'], fact['object'], fact.get('new_status', 'PUBLIC')])
            if key in self.seen:
                continue
            d = dict(evidence_id='K'+key[:16], source_action=action, observed_step=step,
                knowledge_type=kind, subject=fact['subject'], relation=fact['relation'], object=copy.deepcopy(fact['object']),
                previous_status='UNKNOWN', new_status=fact.get('new_status', 'PUBLIC'), related_blocker=None,
                provenance=copy.deepcopy(fact['provenance']), freshness='INITIAL' if initial else 'NEW')
            self.seen[key] = d['evidence_id']
            self.deltas.append(d)
            if not initial:
                new.append(copy.deepcopy(d))
        return new

    @staticmethod
    def relation(delta, blocker):
        """A typed public subject/object link, never a lexical similarity score."""
        if delta['knowledge_type'] not in SUPPORTED_TYPES:
            return 'UNKNOWN'
        entities = set(blocker.get('public_entities', [])) | {blocker.get('subject')}
        obj = delta['object']
        endpoints = {delta['subject']} | ({obj} if isinstance(obj, str) else set())
        return 'PUBLIC_ENTITY_LINK' if entities & endpoints else 'UNKNOWN'

    def eligible(self, blocker):
        return [copy.deepcopy(d) for d in self.deltas
            if d['freshness'] == 'NEW' and d['evidence_id'] not in self.consumed
            and self.relation(d, blocker) != 'UNKNOWN']

    def offer(self, blocker, entries, *, step, risk, request_available=True, budget_available=True):
        ident = blocker_id(blocker)
        related = self.eligible(blocker)
        available = [e for e in entries if e.get('legal') and not e.get('attempted')
            and e.get('transit_steps', 0) <= MAX_TRANSIT_STEPS]
        reasons = []
        if not blocker.get('unresolved'): reasons.append('no_unresolved_blocker')
        if not related: reasons.append('no_unconsumed_publicly_related_new_evidence')
        if not available: reasons.append('no_bounded_public_entry')
        if risk: reasons.append('current_public_risk')
        if step >= MAX_ACTIONS: reasons.append('environment_budget')
        if len(self.grants) >= EXTRA_CREDITS: reasons.append('global_credit_limit')
        if sum(g['blocker_id'] == ident for g in self.grants) >= CREDITS_PER_BLOCKER: reasons.append('blocker_credit_limit')
        if not budget_available: reasons.append('cost_budget')
        # Deterministic offers need no model request; this is recorded explicitly.
        self.last_check = dict(blocker_id=ident, step=step, eligible_evidence=[d['evidence_id'] for d in related],
            legal_entries=len(available), reasons=reasons, deterministic_no_request=True,
            model_request_available=request_available)
        if reasons: return None
        evidence, entry = related[0], copy.deepcopy(available[0])
        evidence['related_blocker'] = ident
        if step + entry.get('transit_steps', 0) + 1 > MAX_ACTIONS:
            self.last_check['reasons'].append('insufficient_actions_for_bounded_probe')
            return None
        grant = dict(id='ETBR'+str(len(self.grants)+1), blocker_id=ident, blocker=copy.deepcopy(blocker),
            evidence_id=evidence['evidence_id'], evidence=copy.deepcopy(evidence),
            evidence_relation=self.relation(evidence, blocker), entry=entry, start_step=step,
            transit_limit=MAX_TRANSIT_STEPS, transit_used=0, probe_used=0, status='active', actions=[],
            stage_events=[], ended_step=None, knowledge_gains=[], material_gains=[],
            precondition_resolved=False, parent_task_resumed=False, task_progress=False)
        self.consumed.append(evidence['evidence_id'])
        self.grants.append(grant)
        self.events.append(dict(event='CREDIT_GRANTED', step=step, grant_id=grant['id'], evidence_id=evidence['evidence_id'], blocker_id=ident))
        return copy.deepcopy(grant)

    def finish(self, ident, status, step):
        g = next(g for g in self.grants if g['id'] == ident)
        g.update(status=status, ended_step=step)
        self.events.append(dict(event='CREDIT_CLOSED', step=step, grant_id=ident, reason=status))

    def to_dict(self): return copy.deepcopy(self.__dict__)

    @classmethod
    def from_dict(cls, data):
        obj = cls(); obj.__dict__.update(copy.deepcopy(data)); return obj

