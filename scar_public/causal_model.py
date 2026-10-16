"""Public-history-only, falsifiable LLM transition proposals.

This is a shadow adapter, not a learned simulator with a coverage guarantee.
Missing facts/effects stay unknown. Sources establish provenance, not truth.
All quantities use exact integer milli-units (1000 == one item).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from fractions import Fraction


SCALE = 1000
PREFIXES = ('craft ', 'pick up ', 'drop ', 'enter ', 'write ', 'inspect ')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def amounts(text):
    if text == 'no objects':
        return {}
    parts = text.split(', ')
    answer = {}
    for part in parts:
        match = re.fullmatch(r'(\d+(?:\.\d+)?) ([\w-]+)', part)
        if not match:
            return None  # An incomplete parse cannot establish zero for omitted objects.
        value = Fraction(match[1]) * SCALE
        if value.denominator != 1:
            return None
        answer[match[2]] = int(value)
    return answer


def project(text, fields):
    """Read only fresh observations; never forward-fill mutable properties."""
    result, stores = {}, {}
    for line in text.splitlines():
        if line.startswith('Current Location: '):
            result['location'] = line[len('Current Location: '):].strip()
        for prefix, suffix, key in (
            ('I am holding ', '.', 'holding'), ('I have equipped ', '.', 'equipped'),
            ('I see ', ' near me.', 'ground')):
            if line.startswith(prefix) and line.endswith(suffix):
                stores[key] = amounts(line[len(prefix):-len(suffix)])
    inspected = re.search(r'^I inspected ([\w-]+):', text, re.M)
    written = re.search(r'^It writes: (.*)$', text, re.M)
    if inspected and written:
        result['text:' + inspected[1]] = written[1]
    elif inspected and 'nothing written' in text:
        result['text:' + inspected[1]] = ''
    for field in fields:
        if ':' not in field:
            continue
        store, item = field.split(':', 1)
        if store in stores and stores[store] is not None:
            result[field] = stores[store].get(item, 0)
    return {k: v for k, v in result.items() if k in fields}


def outcome(text, action):
    """Operation status, deliberately independent of task completion."""
    target = action.split()[-1]
    success = []
    failure = []
    if action.startswith('craft '):
        success = [rf'I successfully crafted [\d.]+ {re.escape(target)}\.']
        failure = [rf'Cannot craft (?:a single )?{re.escape(target)}(?:\.|,)']
    elif action.startswith('pick up '):
        success = [rf'I picked up {re.escape(action[8:])}\.']
        failure = [rf'Cannot pick up {re.escape(action[8:])}(?:\.|,)']
    elif action.startswith('drop '):
        success = [rf'I dropped {re.escape(action[5:])}\.']
        failure = [rf'Cannot drop {re.escape(action[5:])}(?:\.|,)']
    elif action.startswith('enter '):
        success = [rf'I entered {re.escape(action[6:])}\.']
        failure = [rf'Cannot enter {re.escape(action[6:])}(?:\.|,)']
    elif action.startswith('write '):
        success = [rf'I wrote on {re.escape(target)}:']
        failure = [rf'Cannot write on {re.escape(target)}(?:\.|,)']
    elif action.startswith('inspect '):
        success = [rf'I inspected {re.escape(target)}:']
        failure = [rf'Cannot inspect {re.escape(target)}(?:\.|,)']
    yes = any(re.search(p, text) for p in success)
    no = any(re.search(p, text) for p in failure)
    return 'success' if yes and not no else 'failure' if no and not yes else None


def predicate(guard, state):
    unknown = False
    for atom in guard:
        name, op, value = atom['field'], atom['op'], atom['value']
        if name not in state:
            unknown = True
            continue
        actual = state[name]
        valid = actual == value if op == 'eq' else actual >= value if op == 'ge' else actual <= value
        if not valid:
            return False
    return None if unknown else True


def predict(rule, current):
    if predicate(rule['guard'], current) is not True:
        return None
    values = {}
    for effect in rule['effects']:
        field, op = effect['field'], effect['op']
        if op == 'set':
            values[field] = effect['value']
        elif field in current:
            values[field] = current[field] + effect['value'] if op == 'add' else current[field]
        # No invented starting value for a currently unobserved field.
    if rule['result'] != 'unknown':
        values['result'] = rule['result']
    return values


SYSTEM = '''Propose falsifiable LOCAL transition hypotheses from public text. You are NOT
translating the final task or certifying a method. The input contains ONLY past/current
observations and the imminent command. Never use a future outcome. A quote proves its
presence, not the causal rule. Return JSON, with at most TWO hypotheses. If unsupported,
return an empty hypotheses list and explain the unresolved conditions. Do not invent an
alternative just to fill the schema. Each hypothesis is a conditional prediction, not a
fact. Under-specified prerequisites belong in unknowns, not invented Boolean variables.
Schema:
{"reasoning":"brief", "action":"EXACT supplied command", "hypotheses":[
 {"id":"short_id", "guard":[{"field":"holding:ore","op":"ge","value":1000}],
  "effects":[{"field":"holding:ore","op":"add","value":-1000},
             {"field":"ground:bar","op":"add","value":1000},
             {"field":"location","op":"same"}],
  "result":"success", "evidence":[{"observation":0,"quote":"EXACT supplied excerpt"}],
  "unknowns":["unverified prerequisite or scope limitation"]}], "unresolved":["..."]}
Only listed field names are legal. Numeric quantities are integer MILLI-UNITS: one item
is 1000, half an item 500. guard op: eq/ge/le (ge/le only numeric). effect op: add/set/same
(add only numeric). same explicitly predicts unchanged state; OMIT an effect if unknown.
Keep numeric effects as constant changes (add), not a new total (set). Symbol effects use
set or same. result is success/failure/unknown for THIS command, never task completion.
Use exact concrete item IDs, full location strings and full document contents. A fresh
write acceptance does not expose full final text. Do not assume crafting outputs are held.
When repairing, address the supplied mismatches. Do not rename and repeat a rejected rule,
or invent an unseen tool/station as established fact. Cite only evidence supplied here.
'''


class ProposalError(ValueError):
    def __init__(self, message, usage=None):
        super().__init__(message)
        self.usage = usage or {}


class CausalMonitor:
    def __init__(self):
        self.observations = []
        self.actions = []
        self.fields = {'location': 'symbol'}
        self.rules = {}
        self.version = 0
        self.pending = None
        self.events = []
        self.rejected = set()
        self.certificates = []
        self.admission_checks = []

    def _register(self, text):
        items = set()
        for line in text.splitlines():
            for prefix, suffix in (('I am holding ', '.'), ('I have equipped ', '.'),
                                   ('I see ', ' near me.')):
                if line.startswith(prefix) and line.endswith(suffix):
                    items.update(amounts(line[len(prefix):-len(suffix)]) or {})
            if 'It can be used to craft:' in line:
                for target, parts in re.findall(r'([\w-]+) \(([^()]*)\)', line):
                    items.add(target)
                    items.update(amounts(parts) or {})
        inspected = re.search(r'^I inspected ([\w-]+):', text, re.M)
        if inspected:
            items.add(inspected[1])
            self.fields['text:' + inspected[1]] = 'symbol'
        for target, station in re.findall(r'Cannot craft ([\w-]+)\. Missing necessary ([\w-]+)', text):
            items.update((target, station))
        for name in items:
            for store in ('holding', 'ground', 'equipped'):
                self.fields[store + ':' + name] = 'numeric'

    def invalidate(self, reason):
        self.version += 1
        for cert in self.certificates:
            cert['valid'] = False
        self.events.append({'kind': 'version', 'version': self.version, 'reason': reason})

    def observe(self, text, previous_action=None):
        if self.observations:
            if not isinstance(previous_action, str) or not previous_action:
                raise ValueError('Every new public observation requires its preceding action')
            self.actions.append(previous_action)
        elif previous_action is not None:
            raise ValueError('Initial public observation has no preceding action')
        self._register(text)
        self.observations.append(text)
        if self.pending:
            pending, self.pending = self.pending, None
            if previous_action != pending['action']:
                self.events.append({'kind': 'discarded_prediction', 'reason': 'different action executed'})
                return None
            actual = project(text, self.fields)
            result = outcome(text, previous_action)
            if result is not None:
                actual['result'] = result
            checked = []
            for item in pending['predictions']:
                expected = item['values']
                mismatch = {k: {'expected': v, 'observed': actual[k]} for k, v in expected.items()
                            if k in actual and actual[k] != v}
                matched = [k for k, v in expected.items() if k in actual and actual[k] == v]
                absent = [k for k in expected if k not in actual]
                verdict = 'contradicted' if mismatch else 'partially_observed' if absent else 'matched'
                if not expected or not (mismatch or matched):
                    verdict = 'unobserved'
                checked.append({'id': item['id'], 'fingerprint': item['fingerprint'],
                                'verdict': verdict, 'mismatches': mismatch,
                                'matched_fields': matched, 'unobserved_fields': absent})
                if mismatch:
                    self.rejected.add(item['fingerprint'])
                    for rule in self.rules.get(previous_action, []):
                        if rule['fingerprint'] == item['fingerprint']:
                            rule['status'] = 'rejected'
            event = {'kind': 'feedback', 'action': previous_action,
                     'prediction_version': pending['version'], 'prefix_hash': pending['prefix_hash'],
                     'observation': len(self.observations)-1, 'checks': checked}
            self.events.append(event)
            if any(c['verdict'] == 'contradicted' for c in checked):
                self.invalidate('fresh public counterexample')
            return event
        return None

    @property
    def current(self):
        return project(self.observations[-1], self.fields) if self.observations else {}

    @property
    def prefix_hash(self):
        return digest({'observations': self.observations, 'actions': self.actions})

    def context(self, action):
        """Bounded deterministic retrieval; never sees an unexecuted transition."""
        target = action.split()[-1]
        terms = {t for t in re.split(r'[_\W]+', target) if t and not t.isdigit()}
        indices = set(range(max(0, len(self.observations)-3), len(self.observations)))
        relevant = []
        for i, text in enumerate(self.observations[:-3]):
            evidence = '\n'.join(line for line in text.splitlines() if not line.startswith((
                'I am holding ', 'I have equipped ', 'I see ', 'My ', 'Current Time:', 'Neighboring areas:')))
            if any(t.lower() in evidence.lower() for t in terms):
                score = (5*('It can be used to craft:' in evidence) + 3*('Cannot ' in evidence)
                         + 2*('I inspected ' in evidence) + 1)
                relevant.append((score, i))
        indices.update(i for _, i in sorted(relevant)[-9:])
        # Exact same-command evidence plus examples of the same operation on other
        # operands. These are observations to reason from, never universal laws.
        verb = next((p for p in PREFIXES if action.startswith(p)), action.split()[0] + ' ')
        same = [i for i, old in enumerate(self.actions) if old == action]
        related = [i for i, old in enumerate(self.actions) if old.startswith(verb) and
                   outcome(self.observations[i+1], old) == 'success' and old != action]
        transition_indices = sorted(set(same[-3:] + related[-2:]))
        for i in transition_indices:
            indices.update((i, i+1))
        sources = []
        for i in sorted(indices):
            sources.append({'observation': i, 'preceding_action': self.actions[i-1] if i else None,
                            'text': self.observations[i]})
        return {'schema': 'scar.causal.v1', 'action': action, 'quantity_scale': SCALE,
                'prefix_observations': len(self.observations), 'prefix_hash': self.prefix_hash,
                'fields': self.fields, 'fresh_values': self.current, 'sources': sources,
                'observed_transitions': [{'action': self.actions[i], 'before_observation': i,
                    'after_observation': i+1, 'before': project(self.observations[i], self.fields),
                    'after': project(self.observations[i+1], self.fields),
                    'result': outcome(self.observations[i+1], self.actions[i]),
                    'scope': 'one observed transition; different operands require a new hypothesis'}
                    for i in transition_indices],
                'previous_hypotheses': self.rules.get(action, []),
                'counterexamples': [e for e in self.events if e['kind'] == 'feedback'
                                    and e['action'] == action][-3:]}

    def validate(self, proposal, context):
        def need(condition, message):
            if not condition:
                raise ProposalError(message)
        need(isinstance(proposal, dict), 'proposal must be an object')
        need(proposal.get('action') == context['action'], 'action mismatch')
        need(context['prefix_hash'] == self.prefix_hash, 'stale proposal prefix')
        rules = proposal.get('hypotheses')
        need(isinstance(rules, list) and len(rules) <= 2, 'at most two hypotheses')
        need(isinstance(proposal.get('unresolved'), list) and all(isinstance(x, str)
             and len(x) <= 500 for x in proposal['unresolved']), 'unresolved must be short strings')
        sources = {s['observation']: s['text'] for s in context['sources']}
        kept, ids = [], set()
        for raw in rules:
            need(isinstance(raw, dict), 'hypothesis must be an object')
            rule = copy.deepcopy(raw)
            name = rule.get('id')
            need(isinstance(name, str) and re.fullmatch(r'[\w-]{1,60}', name) and name not in ids,
                 'unique short hypothesis id required')
            ids.add(name)
            need(rule.get('result') in ('success', 'failure', 'unknown'), 'bad result')
            need(isinstance(rule.get('unknowns'), list) and all(isinstance(x, str) and len(x) <= 500
                 for x in rule['unknowns']), 'unknowns must be short strings')
            evidence = rule.get('evidence')
            need(isinstance(evidence, list) and 1 <= len(evidence) <= 4, 'one to four public citations required')
            for citation in evidence:
                need(isinstance(citation, dict), 'citation must be an object')
                i, quote = citation.get('observation'), citation.get('quote')
                need(type(i) is int and i in sources and isinstance(quote, str) and
                     8 <= len(quote) <= 800 and quote in sources[i], 'citation absent from supplied public prefix')
            for key in ('guard', 'effects'):
                atoms = rule.get(key)
                need(isinstance(atoms, list) and len(atoms) <= 12, 'bounded guard/effects required')
                seen = set()
                for atom in atoms:
                    need(isinstance(atom, dict), 'atom must be an object')
                    field, op = atom.get('field'), atom.get('op')
                    need(isinstance(field, str) and field in self.fields, 'unknown field')
                    numeric = self.fields[field] == 'numeric'
                    need(op in (('eq', 'ge', 'le') if key == 'guard' else ('add', 'set', 'same')), 'bad operator')
                    need(numeric or op not in ('ge', 'le', 'add'), 'numeric operator on symbol')
                    if key == 'effects':
                        need(field not in seen, 'duplicate effect')
                        seen.add(field)
                        need(not numeric or op != 'set', 'numeric effects must be constant add or same')
                    if op != 'same':
                        value = atom.get('value')
                        need((type(value) is int and abs(value) <= 1_000_000) if numeric else
                             (isinstance(value, str) and len(value) <= 1000), 'invalid value type/range')
            # Ignore prose/ids/citations in identity: renaming a counterexample is not repair.
            core = {k: rule[k] for k in ('guard', 'effects', 'result')}
            core['guard'] = sorted(core['guard'], key=lambda a: json.dumps(a, sort_keys=True))
            core['effects'] = sorted(core['effects'], key=lambda a: a['field'])
            rule['fingerprint'] = digest({'action': context['action'], **core})
            need(rule['fingerprint'] not in self.rejected, 'unchanged previously contradicted hypothesis')
            rule['status'] = 'candidate'
            kept.append(rule)
        return kept

    def historical_conflicts(self, rule, action):
        """Exact command only. No inter-object semantic transfer by the validator."""
        conflicts = []
        for i, previous_action in enumerate(self.actions):
            if previous_action != action:
                continue
            expected = predict(rule, project(self.observations[i], self.fields))
            if expected is None:
                continue
            actual = project(self.observations[i+1], self.fields)
            status = outcome(self.observations[i+1], action)
            if status:
                actual['result'] = status
            mismatch = {k: {'expected': v, 'observed': actual[k]} for k, v in expected.items()
                        if k in actual and actual[k] != v}
            if mismatch:
                conflicts.append({'before_observation': i, 'after_observation': i+1,
                                  'mismatches': mismatch})
        return conflicts

    def install(self, proposal, context):
        kept = self.validate(proposal, context)  # atomic: invalid proposal changes nothing
        for rule in kept:
            conflicts = self.historical_conflicts(rule, context['action'])
            if conflicts:
                rule['status'] = 'rejected_by_public_history'
                self.rejected.add(rule['fingerprint'])
            self.admission_checks.append({'action': context['action'], 'id': rule['id'],
                'prefix_hash': self.prefix_hash, 'status': rule['status'], 'conflicts': conflicts})
        self.invalidate('new candidate model; truth/coverage not established')
        self.rules[context['action']] = kept
        self.events.append({'kind': 'proposal', 'version': self.version, 'action': context['action'],
                            'prefix_hash': self.prefix_hash, 'hypotheses': kept,
                            'unresolved': proposal['unresolved']})
        return kept

    def certificate_is_current(self, certificate):
        return (certificate['valid'] and certificate['model_version'] == self.version
                and certificate['prefix_hash'] == self.prefix_hash)

    def prepare(self, action):
        if self.pending is not None:
            raise ValueError('Consume or explicitly discard the previous prediction first')
        predictions = []
        for rule in self.rules.get(action, []):
            if rule['status'] != 'candidate':
                continue
            values = predict(rule, self.current)
            if values is not None:
                predictions.append({'id': rule['id'], 'fingerprint': rule['fingerprint'], 'values': values})
        self.pending = {'action': action, 'version': self.version, 'prefix_hash': self.prefix_hash,
                        'observation': len(self.observations)-1, 'predictions': predictions}
        return copy.deepcopy(self.pending)

    def state(self):
        return {**copy.deepcopy(vars(self)), 'rejected': sorted(self.rejected)}

    @classmethod
    def load(cls, data):
        obj = cls()
        for key in vars(obj):
            if key in data:
                setattr(obj, key, copy.deepcopy(data[key]))
        obj.rejected = set(obj.rejected)
        return obj


def request_proposal(provider, monitor, action):
    """One audited request, no silent repair loop and no task/engine access."""
    context = monitor.context(action)
    result = provider.request([{'role': 'system', 'content': SYSTEM},
                               {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}])
    choice = result['choices'][0]
    usage = result.get('usage', {})
    if choice.get('finish_reason') == 'length':
        raise ProposalError('truncated proposal', usage)
    try:
        proposal = json.loads(choice['message']['content'])
    except (ValueError, KeyError, TypeError) as error:
        raise ProposalError('malformed JSON proposal', usage) from error
    try:
        monitor.install(proposal, context)
    except ProposalError as error:
        error.usage = usage
        raise
    return proposal, usage
