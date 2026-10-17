"""Scoped, revocable continuation repair from *executed* public transitions.

No evaluator, game identifier, entity-specific rule or counterfactual simulator
enters this module. Repetition is a heuristic trigger, not an impossibility
certificate. The original actor remains authoritative without a repair trigger.
"""
import copy
import json
import re

from scar_public.causal_model import digest
from scar_public.public_model import state_from_text
from scar_public.core_planner import CorePlannerAgent


FAILURE = re.compile(r'^(?:Cannot\b|Invalid action\.|Do not have sufficient amount)', re.M)
PROTECTED = ('attack ', 'defend', 'eat ', 'drink ', 'sleep', 'rest', 'flee', 'run ')
OBSERVATIONAL = ('enter ', 'inspect ', 'talk to ')


def feedback_lines(text):
    return [line.strip() for line in text.splitlines() if FAILURE.match(line.strip())]


def threatened(text):
    return 'I was attacked' in text or 'has blocked the way out' in text


def nearby(text):
    match = re.search(r'^I see (.+) nearby\.$', text, re.M)
    return [] if not match or match[1] == 'no one' else match[1].split(', ')


def public_facts(text):
    """New report content, excluding clocks, action acknowledgements and failures.

    This adapter is intentionally separate from the decision rule. Exact text
    novelty is conservative: paraphrases can suppress a trigger, not prove one.
    """
    excluded = ('Current ', 'My ', 'I am holding ', 'I have equipped ', 'I see ',
                'Neighboring areas:', 'Cannot ', 'Invalid action.',
                'I entered ', 'I talked to ', 'I was attacked', 'I attacked ',
                'I picked up ', 'I dropped ', 'I equipped ', 'I unequipped ',
                'I stored ', 'I took out ', 'I successfully crafted ',
                'I ate ', 'I drank ', 'I defended ', 'I waited')
    return {line.strip() for line in text.splitlines() if line.strip()
            and not line.strip().startswith(excluded)}


class ContinuationMemory:
    """Finite observed evidence, with progress invalidation and retry expiry."""
    def __init__(self):
        self.facts = set()
        self.locations = {}
        self.epoch = 0
        self.pending = None
        self.records = []
        self.observation = None
        self.current = {}
        self.step = -1
        self.last_outcome = None
        self.repair_attempts = []

    def observe(self, text, step):
        if step == self.step:
            if text != self.observation:
                raise ValueError('Two different observations at one decision index')
            return
        state = state_from_text(text)
        new_facts = public_facts(text) - self.facts
        place = state.get('location')
        layout = (tuple(state.get('neighbors', [])), tuple(sorted((state.get('ground') or {}).keys())))
        discovery = place not in self.locations or self.locations.get(place) != layout
        self.locations[place] = layout
        self.facts.update(new_facts)
        changed_resources = bool(self.pending) and any(
            self.pending['before'].get(k) != state.get(k) for k in ('holding', 'equipped'))
        progress = bool(new_facts or discovery or changed_resources)
        previous_epoch = self.epoch
        if progress:
            self.epoch += 1
        if self.pending:
            record = {**self.pending, 'after': copy.deepcopy(state), 'feedback': feedback_lines(text),
                      'progress': progress, 'epoch_after': self.epoch,
                      'protected': self.pending['protected'] or threatened(text)}
            self.records.append(record)
            self.records = self.records[-64:]
            self.last_outcome = dict(step=step, action=record['action'], progress=progress,
                new_facts=sorted(new_facts), resource_change=changed_resources,
                discovery=discovery, failures=record['feedback'],
                revoked_previous_epoch=self.epoch != previous_epoch)
        self.pending = None
        self.current = state
        self.observation = text
        self.step = step

    def context(self, action, task):
        # Never equate unobserved inventories with observed empty inventories.
        if any(self.current.get(k) is None for k in ('location', 'holding', 'equipped', 'ground')):
            return None
        scope = {k: self.current.get(k) for k in ('location', 'holding', 'equipped', 'neighbors')}
        if not action.startswith(('enter ', 'talk to ')):
            scope['ground'] = self.current.get('ground')
        if action.startswith('talk to '):
            scope['target_present'] = action[8:] in nearby(self.observation)
        return digest(dict(scope=scope, task=task, epoch=self.epoch))

    def assess(self, action, task=''):
        if action.startswith(PROTECTED) or threatened(self.observation or ''):
            return None
        context = self.context(action, task)
        if context is None:
            return None
        matched = [r for r in self.records if r['action'] == action and r['context'] == context
                   and not r['protected'] and not r['progress']]
        # One actual rejected execution suffices for a short deferral. It is not
        # extrapolated after resource/information changes or beyond six actions.
        failures = [r for r in matched if r['feedback'] and self.step - r['step'] <= 6]
        if failures:
            return dict(kind='REPEATED_OBSERVED_FAILURE', action=action, context=context,
                        witnesses=[dict(step=r['step'], feedback=r['feedback']) for r in failures],
                        expiry=max(r['step'] for r in failures)+6,
                        qualification='Same observed context; omitted conditions remain possible')
        # Movement alone can be a useful intermediate step. Require two prior
        # repetitions with no intervening new information or carried-state change.
        repeats = [r for r in matched if self.step-r['step'] <= 24]
        if action.startswith(OBSERVATIONAL) and len(repeats) >= 2:
            return dict(kind='REPEATED_WITHOUT_OBSERVED_PROGRESS', action=action, context=context,
                        witnesses=[dict(step=r['step'], feedback=r['feedback']) for r in repeats],
                        expiry=max(r['step'] for r in repeats)+24,
                        qualification='Heuristic; absence of observed progress is not impossibility')
        return None

    def commit(self, action, task=''):
        self.pending = dict(action=action, task=task, step=self.step, epoch=self.epoch,
                            context=self.context(action, task), before=copy.deepcopy(self.current),
                            protected=threatened(self.observation or '') or action.startswith(PROTECTED))

    def offered(self, trigger):
        """A soft warning cannot demand repeated reconsideration in one context."""
        if trigger['kind'] != 'REPEATED_WITHOUT_OBSERVED_PROGRESS':
            return False
        return any(r['context']==trigger['context'] and r['action']==trigger['action']
                   and self.step-r['step']<=24 for r in self.repair_attempts)

    def mark_offered(self, trigger):
        self.repair_attempts.append(dict(context=trigger['context'],action=trigger['action'],step=self.step))
        self.repair_attempts=self.repair_attempts[-64:]

    def state(self):
        return {**vars(self), 'facts': sorted(self.facts)}


def task_key(memory):
    return digest(sorted(r['quote'] for r in memory.progress_tasks.values()))


def visible_options(memory, text):
    """Non-consuming first actions only; task value is assessed by the LLM.

    Movement and dialogue may still have environmental costs. Membership is an
    interface/access check, not a survival or full-task preservation certificate.
    """
    s = memory.model.current
    actions = ['enter '+n for n in s.get('neighbors', [])]
    actions += ['talk to '+n for n in nearby(text)]
    visible = sorted(set(s.get('holding') or {}) | set(s.get('ground') or {}) | set(s.get('equipped') or {}))
    actions += ['inspect '+n for n in visible]
    return list(dict.fromkeys(actions))


def select_repair(original, response, packet, evidence, task, mode='repair'):
    """Choose once from a bounded shared candidate set; unknown => original.

    A citation establishes provenance only. Goal relevance and expected benefit
    remain LLM heuristics; no candidate is advertised as a theorem-backed plan.
    """
    if mode not in ('advice', 'repair'):
        raise ValueError(mode)
    if packet['epoch'] != evidence.epoch or packet['context'] != evidence.context(original['action'], task):
        return original, dict(reason='STALE_REPAIR_PACKET', changed=False, rejected=[])
    candidates = [response] + (response.get('alternatives') if isinstance(response.get('alternatives'), list) else [])[:3]
    rejected = []
    eligible = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        action = candidate.get('action', '')
        if not isinstance(action, str):
            rejected.append(dict(action=None, reasons=['MALFORMED_ACTION']))
            continue
        reasons = []
        if action not in packet['options']:
            reasons.append('FIRST_ACTION_NOT_IN_OBSERVED_MENU')
        risk = evidence.assess(action, task)
        # A traversal appearing in a cycle may be essential to leave the current
        # room. Only an observed failed execution justifies hard short deferral.
        if risk and risk['kind']=='REPEATED_OBSERVED_FAILURE':
            reasons.append(risk['kind'])
        if reasons:
            rejected.append(dict(action=action, reasons=reasons))
        else:
            eligible.append(candidate)
    # The advice arm gets exactly the same packet and proposals but leaves the
    # final proposal with the actor. It may choose outside the bounded menu.
    chosen = response if mode == 'advice' else (eligible[0] if eligible else None)
    if not chosen or chosen.get('action') == original['action']:
        return original, dict(reason='NO_ADMITTED_DIFFERENCE', changed=False, rejected=rejected)
    result = {**original, 'action': chosen['action'],
              'reasoning': chosen.get('reasoning', response.get('reasoning', 'Evidence-conditioned continuation')),
              'frame': {**original.get('frame', {}),
                        # Preserve the goal by construction instead of asking
                        # the LLM to retranslate/recite it for every alternative.
                        'goal_quote': packet['goals'][0],
                        'method': chosen.get('reasoning', response.get('reasoning', 'Revise failed continuation')),
                        'assessment': packet['trigger']['kind'],
                        'expected': chosen.get('expected') or chosen.get('frame', {}).get('expected') or
                                    'Observe the result of '+chosen['action']+'; task completion remains unconfirmed.'}}
    # A stale recipe target cannot silently redirect the next decision back to
    # the rejected method; this is recorded as part of the actual intervention.
    result.pop('resource_target', None)
    return result, dict(reason='ACTOR_REPAIR' if mode == 'advice' else 'CHECKED_CONTINUATION',
                        changed=True, rejected=rejected, selected=chosen,
                        support='First action is in the currently observed interface menu; task relevance remains heuristic')


class ContinuationAgent(CorePlannerAgent):
    def __init__(self, llm, system_prompt, repair_mode='repair'):
        super().__init__(llm, system_prompt, mode='checked')
        if repair_mode not in ('off', 'advice', 'repair'):
            raise ValueError(repair_mode)
        self.continuation = ContinuationMemory()
        self.repair_mode = repair_mode
        self.continuation_events = []

    def act(self, obs):
        self.continuation.observe(obs['text'], self.llm.step)
        return super().act(obs)

    def finalize_decision(self, executed, obs, step, prompt, query):
        evidence = self.continuation
        task = task_key(self.notebook)
        trigger = evidence.assess(executed['action'], task)
        event = dict(step=step, original=executed['action'], trigger=trigger, changed=False)
        if trigger and self.repair_mode != 'off' and not evidence.offered(trigger):
            # A quote rejected by the persistent task parser may still be an
            # exact public task anchor. It is not promoted into a terminal spec.
            quote = executed.get('frame', {}).get('goal_quote', '')
            if not (len(quote)>=12 and any(quote in t for t in self.notebook.observations)):
                quote=self.notebook.frame.get('goal_quote','')
            goals=[quote] if len(quote)>=12 and any(quote in t for t in self.notebook.observations) else []
            options = visible_options(self.notebook, obs['text'])
            if goals and options:
                packet = dict(trigger=trigger, epoch=evidence.epoch,
                    context=evidence.context(executed['action'], task), goals=goals, options=options,
                    public_support=obs['text']+'\n'+'\n'.join(self.notebook.model.source_lines),
                    recent_attempts=[dict(action=r['action'],step=r['step'],feedback=r['feedback'],progress=r['progress'])
                                     for r in evidence.records[-12:]],
                    qualification='Heuristic method repair. Source quotes do not certify task sufficiency; no survival guarantee.')
                instruction = ('\nContinuation repair packet:\n'+json.dumps(packet, ensure_ascii=False, sort_keys=True)+
                    '\nThe original action has the listed observed repetition evidence. Keep the original task. '
                    'Select a useful next action from options, or keep the original if every alternative is worse. '
                    'Prefer resolving the failed method or making concrete task progress over unrelated novelty. '
                    'Do not treat revisiting, necessary repetition or an unknown condition as impossibility. '
                    'The anchored goal is fixed; do not redefine it. Return reasoning, action, '
                    'expected (a concrete observable change), and alternatives (at most 3 different candidate objects '
                    'with those fields, in preference order). All candidates must serve the same anchored goal. '
                    'For a repetition warning, you may keep a necessary transit action; it is not a failed action. '
                    'The menu avoids deliberate consumption; time, travel and danger still cost resources.')
                response = query(prompt+instruction)
                evidence.mark_offered(trigger)
                result, selection = select_repair(executed, response, packet, evidence, task, self.repair_mode)
                event.update(selection, packet=packet, proposal=response)
                executed = result
            else:
                event['reason'] = 'NO_PUBLIC_TASK_OR_AVAILABLE_OPTION'
        evidence.commit(executed['action'], task)
        event['executed'] = executed['action']
        self.continuation_events.append(event)
        executed['continuation'] = event
        if event['changed']:
            executed['decision_source'] = 'scar_continuation'
        return executed

    def observe_terminal(self, obs):
        self.continuation.observe(obs['text'], self.llm.step+1)
        super().observe_terminal(obs)
