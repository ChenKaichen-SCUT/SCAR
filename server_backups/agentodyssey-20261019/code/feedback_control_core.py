"""Observation-only control state. No game rules, hidden state, or rewards."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import re
import shlex

STATE_PREFIXES = ('Current Location:', 'I am holding ', 'I have equipped ',
                  'I see ', 'My level ', 'My attack ', 'My defense ',
                  'My health ', 'My experience ', 'Neighboring areas:')
DENIAL = re.compile(r"^(?:Cannot\b|Can't\b|Invalid\b|Failed\b|Not enough\b)", re.I)

def norm(text):
    return ' '.join(str(text).strip().split())

def items(value, limit):
    return value[:limit] if isinstance(value, list) else []

def observe(text):
    lines = [norm(x) for x in text.splitlines() if x.strip()]
    state = [x for x in lines if x.startswith(STATE_PREFIXES)]
    feedback = [x for x in lines if not x.startswith(STATE_PREFIXES + ('Current Time:',))]
    location = next((x for x in state if x.startswith('Current Location:')), '')
    signature = hashlib.sha256('\n'.join(sorted(state)).encode()).hexdigest()
    return {'location': location, 'state': state, 'signature': signature,
            'feedback': feedback, 'denials': [x for x in feedback if DENIAL.match(x)]}

def schema_error(action, schemas):
    """Validate only declared verbs/arity. Never enumerate valid game actions."""
    action = norm(action)
    for verb, params in sorted(schemas, key=lambda s: -len(s[0])):
        if action == verb or action.startswith(verb + ' '):
            remainder = action[len(verb):].strip()
            try:
                values = shlex.split(remainder)
            except ValueError:
                return 'Unbalanced quotation marks.'
            # A text parameter can span words. Do not over-constrain it.
            if any(p.lower() in {'text', 'message', 'content', 'query'} for p in params):
                return None if len(values) >= len(params) else 'Missing arguments for ' + verb
            if len(values) != len(params):
                return 'Declared schema: ' + verb + ' ' + ' '.join('<'+p+'>' for p in params)
            return None
    return 'Verb is absent from the declared action space.'

class ControlState:
    def __init__(self):
        self.step = 0
        self.observations = {}
        self.transitions = []
        self.pending = None
        self.rules = {}
        self.guidance = None
        self.last_review = -100
        self.reviews = 0
        self.repairs = 0
        self.audit = []

    def advance(self, observation):
        self.step += 1
        self.observations[self.step] = observation
        view = observe(observation)
        if self.pending:
            t = dict(self.pending)
            t.update({'after_step': self.step, 'after': observation,
                      'after_signature': view['signature'],
                      'feedback': view['feedback'], 'denials': view['denials']})
            self.transitions.append(t)
        return view

    def choose(self, observation, action, reasoning):
        self.pending = {'step': self.step, 'action': norm(action),
                        'reasoning': reasoning, 'before': observation,
                        'before_signature': observe(observation)['signature']}

    def trigger(self):
        if not self.transitions or self.reviews >= 80:
            return None
        if self.step - self.last_review < 3:
            return None
        latest = self.transitions[-1]
        if latest['denials']:
            return 'explicit_environment_denial'
        recent = self.transitions[-8:]
        repeats = Counter((t['action'], '\n'.join(t['feedback'])) for t in recent)
        if repeats and max(repeats.values()) >= 3:
            return 'repeated_action_and_feedback_candidate'
        if self.guidance and self.step >= self.guidance['review_at']:
            return 'expected_effect_checkpoint'
        if self.step - self.last_review >= 12:
            return 'periodic_plan_check'
        return None

    def evidence(self, refs):
        """Validate quotation provenance, NOT the logical truth of an inference."""
        accepted = []
        for ref in items(refs, 6):
            if not isinstance(ref, dict):
                continue
            step, quote = ref.get('step'), ref.get('quote')
            if (isinstance(step, int) and isinstance(quote, str)
                    and 12 <= len(quote) <= 800
                    and quote in self.observations.get(step, '')):
                accepted.append({'step': step, 'quote': quote})
        return accepted

    def select_rules(self, observation):
        """Bounded lexical matching; no extra embedding model or game lexicon."""
        query = set(re.findall(r'[a-z_]{3,}', observation.lower()))
        scored = []
        for rid, rule in self.rules.items():
            if rule['status'] == 'retired':
                continue
            words = set(re.findall(r'[a-z_]{3,}', (rule['condition']+' '+rule['lesson']).lower()))
            scored.append((len(query & words), rule['updated_step'], rid))
        return [self.rules[x[2]] for x in sorted(scored, reverse=True)[:12]]

    def review_input(self, observation, trigger, schemas):
        return {'decision_step': self.step, 'trigger': trigger,
                'action_schema': [{'verb': v, 'params': p} for v,p in schemas],
                'current_observation': {'step': self.step, 'text': observation},
                'recent_transitions': self.transitions[-8:],
                'previous_expectation': self.guidance,
                'candidate_rules': self.select_rules(observation)}

    def apply_review(self, result, trigger):
        self.last_review = self.step
        self.reviews += 1
        accepted, rejected = [], []
        if not isinstance(result, dict):
            self.audit.append({'step': self.step, 'event': 'invalid_review', 'trigger': trigger})
            return
        for item in items(result.get('rules'), 5):
            if not isinstance(item, dict):
                continue
            rid = norm(item.get('id', ''))[:50]
            refs = self.evidence(item.get('evidence', []))
            if not refs or not rid:
                rejected.append({'id': rid, 'reason': 'no_valid_observation_evidence'})
                continue
            status = item.get('status', 'tentative')
            if status not in {'tentative', 'supported', 'retired'}:
                status = 'tentative'
            if status == 'retired' and rid not in self.rules:
                continue
            # An old failure can justify retaining a lesson, but cannot by itself
            # justify withdrawing it after state changes.
            if status == 'retired' and not any(r['step'] > self.rules[rid]['updated_step'] for r in refs):
                rejected.append({'id': rid, 'reason': 'withdrawal_without_new_evidence'})
                continue
            condition, lesson = item.get('condition'), item.get('lesson')
            if not isinstance(condition, str) or not isinstance(lesson, str):
                continue
            self.rules[rid] = {'id': rid, 'condition': condition[:700],
                'lesson': lesson[:900], 'status': status, 'evidence': refs,
                'updated_step': self.step,
                'status_is_model_judgment': True}
            accepted.append(rid)
        refs = self.evidence(result.get('evidence', []))
        # Guidance must have evidence; the hypotheses remain explicitly uncertain.
        if refs:
            horizon = result.get('horizon_steps', 6)
            if not isinstance(horizon, int):
                horizon = 6
            active = []
            for item in items(result.get('applicable_rules'), 5):
                if not isinstance(item, dict) or item.get('id') not in self.rules:
                    continue
                current_refs = self.evidence(item.get('evidence', []))
                if any(e['step'] == self.step for e in current_refs):
                    active.append({'rule': self.rules[item['id']],
                        'applicability': item.get('applicability', 'unknown'),
                        'current_evidence': current_refs})
            self.guidance = {'created_step': self.step, 'review_at': self.step + max(2,min(12,horizon)),
                'diagnosis': str(result.get('diagnosis',''))[:1200],
                'goal': str(result.get('goal',''))[:500],
                'subgoal': str(result.get('subgoal',''))[:700],
                'expected_change': str(result.get('expected_change',''))[:700],
                'hypotheses': str(result.get('hypotheses',''))[:700],
                'previous_effect_assessment': str(result.get('previous_effect_assessment','unknown'))[:600],
                'evidence': refs, 'applicable_rules': active}
        self.audit.append({'step': self.step, 'event': 'review', 'trigger': trigger,
            'accepted_rule_updates': accepted, 'rejected_rule_updates': rejected,
            'guidance_evidence_valid': bool(refs), 'raw_review': result})

    def actor_packet(self, observation):
        view = observe(observation)
        denied = [{'step': t['step'], 'action': t['action'], 'feedback': t['denials']}
                  for t in self.transitions[-8:] if t['denials']]
        guidance = self.guidance if self.guidance and self.step <= self.guidance['review_at'] else None
        return {'current_step': self.step, 'recent_observed_denials': denied,
                'guidance': guidance,
                'guidance_status': 'advisory; recheck against current observation',
                'projected_state_signature': view['signature']}

    def repeated_denial(self, action, observation):
        sig = observe(observation)['signature']
        matched = [t for t in self.transitions[-4:]
                   if t['action'] == norm(action) and t['denials']
                   and t['after_signature'] == sig]
        if len(matched) >= 2:
            return {'reason': 'same action denied twice recently with the same visible state projection',
                    'evidence_steps': [t['after_step'] for t in matched],
                    'feedback': matched[-1]['denials'],
                    'warning': 'Time and hidden state can still have changed. A justified retry remains possible.'}
        return None

    def to_dict(self):
        return {'step': self.step, 'reviews': self.reviews, 'repairs': self.repairs,
                'rules': self.rules, 'guidance': self.guidance,
                'last_review': self.last_review, 'audit': self.audit,
                'recent_transitions': self.transitions[-12:]}
