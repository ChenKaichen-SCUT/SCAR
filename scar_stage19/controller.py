"""Public FIFO execution with persistent subgoals and prerequisite resolution.

The policy accepts observations only. It never imports a world, task catalogue,
evaluator, environment snapshot, or hidden recipe. Original task state is never
reset when installing a temporary intent.
"""
import copy
import re
from scar.io import digest
from scar_sequence.planner import q
from scar_stage17.budget_adapter import Budget100Controller
from scar_stage16.controller import BaselineController
from scar_v3.state import parse_action
from .acquisition import bound_store
from .execution_context import assess
from .config import INTENT_ACTION_LIMIT, EXPLORATORY_ACTION_LIMIT, PRECONDITION_DEPTH_LIMIT, MAX_PLANNING_CALLS
from .planning import validate


class Controller19(Budget100Controller):
    def __init__(self):
        super().__init__('S1_P1_P3')
        self.intent19 = None
        self.intent_log19 = []
        self.acceptance19 = []
        self.request_contexts19 = []
        self.plan_calls19 = 0
        self.blocker19 = {}
        self.preconditions19 = {}
        self.precondition_events19 = []
        self.active_precondition19 = None
        self.probe_candidates19 = []
        self.acquisitions19 = []
        self.audit19 = {}
        self.outcome19 = {}

    def legacy_copy(self):
        obj = Budget100Controller()
        for name in obj.__dict__:
            if name in self.__dict__:
                obj.__dict__[name] = copy.deepcopy(self.__dict__[name])
        return obj

    def _all_needed(self, item, seen=None):
        found, pending = set(seen or ()), [item]
        while pending:
            name = pending.pop(0)
            if name in found:
                continue
            found.add(name)
            rule = self.table.recipes.get(name, {})
            pending += rule.get('ingredients', []) + rule.get('stations', [])
        return found

    def needed(self):
        nodes = self._all_needed(parse_action(self.target).target)
        if self.intent19:
            nodes |= self._all_needed(self.intent19['target'])
        return nodes

    def assess(self, action):
        return assess(self, action)

    def _bound(self, action, **kwargs):
        if not action:
            return None
        action, record = bound_store(self, action, **kwargs)
        if record:
            self.acquisitions19.append(record)
        return action

    def _acquire(self, name, amount, protect, use_container=True):
        return self._bound(super()._acquire(name, amount, protect, use_container),
                           hint=amount, source='FIFO_acquire')

    def local_collect(self, item, amount=1):
        return self._bound(super().local_collect(item, amount), ground_need=amount, source='P3_local_collect')

    def collection(self, item, all_visible=False):
        return self._bound(super().collection(item, all_visible), source='S1_alternative')

    def _probe(self, action, reason, source):
        if not action or self.exploration_spent >= self.EXPLORATION_LIMIT:
            return None
        result = super()._probe(action, reason, source)
        if result:
            self.probe_candidates19.append(dict(action=result, pending=copy.deepcopy(self.pending_probe),
                                                exploration=copy.deepcopy(self.explore_pending)))
        return result

    def _usable(self, action):
        return bool(action and self.assess(action)['status'] != 'REJECT'
                    and self.actual_visits.get(digest([action, self.context(action)]), 0) < 2)

    def block(self, kind, item, **extra):
        self.blocker19 = dict(kind=kind, item=item, **extra)
        return None

    def public_entries(self):
        t = self.table
        return dict(visible=sorted(self.visible()),
            observed_locations={n: sorted(d['objects']) for n, d in sorted(t.places.items())},
            reachable=sorted({n for ns in t.links.values() for n in ns if t.path(n)}),
            inspected=list(t.inspected))

    def locations(self, item):
        return [loc for loc, data in sorted(self.table.places.items())
                if data['objects'].get(item, 0) > 0 and self.table.path(loc)]

    def _free_hand(self):
        t = self.table
        if sum((t.state.get('hands') or {}).values()) < 2:
            return None
        if t.inventory:
            for name, count in sorted((t.state.get('hands') or {}).items()):
                if name not in t.containers:
                    action = self._bound(f'store {int(count)} {q(name)} inventory', source='release_hand')
                    if self._usable(action):
                        return action
        return None

    def known_step(self, item, amount=1, ancestors=(), ground=False):
        """Bounded public prerequisite resolution; does not replace the main FIFO."""
        if item in ancestors or len(ancestors) >= PRECONDITION_DEPTH_LIMIT:
            return self.block('prerequisite_cycle_or_depth_limit', item, chain=list(ancestors))
        t = self.table
        if ground and (t.state.get('ground') or {}).get(item, 0) > 0:
            return None
        if not ground and self.ownership(item)['lower_bound'] >= amount:
            return None
        if ground:
            # Missing-necessary evidence demands presence here, not possession.
            if (t.state.get('hands') or {}).get(item, 0):
                return 'drop ' + q(item)
            if (t.state.get('equipment') or {}).get(item, 0):
                return self._free_hand() or 'unequip ' + q(item)
            for container, data in sorted(t.containers.items()):
                if t.carried(container) and (data.get('counts') or {}).get(item, 0):
                    return self._free_hand() or f'take out {q(item)} {q(container)}'
            for location in self.locations(item):
                action = self._move(location)
                if self._usable(action):
                    return action
        else:
            action = self._acquire(item, amount, self.needed() | set(ancestors))
            if self._usable(action):
                return action
        # Refresh carried contents before treating a lower bound as absence.
        for container, data in sorted(t.containers.items()):
            if t.carried(container) and data.get('counts') is None:
                action = 'inspect ' + q('inventory' if container == t.inventory else container)
                if self._usable(action):
                    return action
        recipe = t.recipes.get(item, {})
        ingredients = recipe.get('ingredients', [])
        if not ingredients:
            return self.block('unknown_recipe_or_acquisition_path', item, requires_ground=ground)
        for dep in ingredients:
            required = (recipe.get('quantities') or {}).get(dep, self.quotas.get(item, 1))
            if self.ownership(dep)['lower_bound'] < required:
                self.queue_needs[dep] = max(self.queue_needs.get(dep, 1), required)
                return self.known_step(dep, required, ancestors + (item,))
        for requirement in recipe.get('stations', []):
            if not (t.state.get('ground') or {}).get(requirement, 0):
                self.active_precondition19 = dict(product=item, required_object=requirement,
                    object_type='UNKNOWN', evidence_ids=recipe.get('evidence_ids', []), chain=list(ancestors))
                return self.known_step(requirement, 1, ancestors + (item,), ground=True)
        candidate = self._batch_action('craft 1 ' + q(item))
        if self._usable(candidate):
            return candidate
        return self.block('known_execution_conditions_blocked', item, assessment=self.assess(candidate))

    def _station(self, product):
        t = self.table
        for item in t.recipes.get(product, {}).get('stations', []):
            if not (t.state.get('ground') or {}).get(item, 0):
                self.active_precondition19 = dict(product=product, required_object=item,
                    object_type='UNKNOWN', evidence_ids=t.recipes[product].get('evidence_ids', []))
                action = self.known_step(item, 1, (product,), ground=True)
                if action and self.active_precondition19:
                    self.active_precondition19['selected_action'] = action
                return action
        return None

    def planning_context(self):
        t = self.table
        rules = {n: {k: r.get(k) for k in ('ingredients','quantities','stations')} for n,r in t.recipes.items()}
        return digest(dict(resources=self._signature(), recipes=rules, inspected=t.inspected,
                           links=t.links, blocker={k:self.blocker19.get(k) for k in ('kind','item','chain')}, risk=self.risk16))

    def can_request(self):
        return self.plan_calls19 < MAX_PLANNING_CALLS and self.planning_context() not in self.request_contexts19

    def start_request(self):
        self.plan_calls19 += 1
        self.request_contexts19.append(self.planning_context())

    def _intent_done(self, intent):
        kind, item, t = intent['type'], intent['target'], self.table
        if kind == 'INSPECT_OBJECT':
            return item in t.inspected
        if kind == 'EXPLORE_FRONTIER':
            return item == t.state.get('location')
        if kind == 'LOCATE_PRECONDITION':
            return bool((t.state.get('ground') or {}).get(item, 0) or self.locations(item)
                        or t.recipes.get(item, {}).get('ingredients'))
        if kind == 'CRAFT_PRECONDITION' and intent.get('crafted'):
            return True
        return self.ownership(item)['lower_bound'] >= intent.get('amount', 1)

    def close_intent(self, status, reason):
        if not self.intent19:
            return
        record = dict(copy.deepcopy(self.intent19), status=status, end_step=self.step16,
                      termination_reason=reason, final_goal_unchanged=self.target == self.intent19['final_goal'])
        self.intent_log19.append(record)
        self.intent19 = None

    def _inspect_entry(self, item):
        t = self.table
        if item in self.visible() or item == 'inventory' and t.inventory:
            return 'inspect ' + q(item)
        for location in self.locations(item):
            if action := self._move(location):
                return action
        return self.block('inspection_entry_no_longer_accessible', item)

    def _intent_step(self):
        intent = self.intent19
        if self._intent_done(intent):
            self.close_intent('completed', 'public_completion_condition')
            return None
        if intent['remaining_actions'] <= 0:
            self.close_intent('expired', 'fixed_intent_action_limit')
            return None
        kind, item = intent['type'], intent['target']
        if kind in ('ACQUIRE_MATERIAL', 'CRAFT_PRECONDITION'):
            action = self.known_step(item, intent['amount'])
        elif kind == 'INSPECT_OBJECT':
            action = self._inspect_entry(item)
        elif kind == 'EXPLORE_FRONTIER':
            action = self._move(item)
        else:
            entry = intent['entry']
            if entry in self.public_entries()['reachable'] or entry == self.table.state.get('location'):
                action = self._move(entry) if entry != self.table.state.get('location') else None
                if not action and entry == self.table.state.get('location'):
                    candidates = [n for n in sorted(self.visible()) if n not in self.table.inspected]
                    action = self._inspect_entry(candidates[0]) if candidates else None
            else:
                action = self._inspect_entry(entry) if entry not in self.table.inspected else None
        if not self._usable(action):
            self.close_intent('blocked', 'public_entry_exhausted_or_conditions_changed')
            return None
        if intent['exploratory']:
            action = self._probe(action, 'accepted_bounded_subgoal', {'intent_id': intent['id'], 'type': kind})
            if not action:
                self.close_intent('expired', 'inherited_exploration_budget_exhausted')
        return action

    def accept(self, proposal, prompt):
        validate(proposal)
        t = self.table; kind, item, entry = (proposal[k] for k in ('type','target','entry'))
        entries = self.public_entries()
        public_objects = set(entries['visible']) | set(t.recipes) | self.needed()
        for data in t.places.values():
            public_objects.update(data['objects'])
        for r in t.recipes.values():
            public_objects.update(r.get('ingredients', []) + r.get('stations', []))
        destinations = set(entries['reachable']) | {t.state.get('location')}
        key = digest([kind, item, entry, self.planning_context()])
        reason = None
        if self.intent19:
            reason = 'unfinished_intent_conflict'
        elif any(s not in prompt or len(s.strip()) < 3 for s in proposal['public_evidence']):
            reason = 'evidence_not_quoted_from_public_prompt'
        elif entry not in public_objects | destinations | ({'inventory'} if t.inventory else set()):
            reason = 'no_public_execution_entry'
        elif item not in public_objects | destinations:
            reason = 'target_not_publicly_named'
        elif any(r['key'] == key for r in self.acceptance19):
            reason = 'duplicate_subgoal_same_conditions'
        elif kind == 'EXPLORE_FRONTIER' and item not in destinations:
            reason = 'no_public_route'
        elif kind == 'INSPECT_OBJECT' and item in t.inspected:
            reason = 'already_inspected'
        elif kind == 'CRAFT_PRECONDITION' and not t.recipes.get(item, {}).get('ingredients'):
            reason = 'recipe_unpublished_not_an_executable_craft_intent'
        related = item in self.needed() or item == self.blocker19.get('item')
        exploratory = not related or kind in ('INSPECT_OBJECT', 'EXPLORE_FRONTIER', 'LOCATE_PRECONDITION')
        if not related and not self.blocker19:
            reason = reason or 'no_connection_to_task_or_blocker'
        if exploratory and self.exploration_spent >= self.EXPLORATION_LIMIT:
            reason = reason or 'inherited_exploration_budget_exhausted'
        record = dict(key=key, proposal=copy.deepcopy(proposal), accepted=False, reason=reason,
                      step=self.step16, evidence_scope='public entry only; hypothesis not promoted to knowledge')
        if reason is None:
            amount = self.amount if item == parse_action(self.target).target else self.queue_needs.get(item, 1)
            intent = dict(copy.deepcopy(proposal), id='sg19_'+str(len(self.acceptance19)+1),
                status='active', start_step=self.step16, steps=0, amount=amount, exploratory=exploratory,
                remaining_actions=EXPLORATORY_ACTION_LIMIT if exploratory else INTENT_ACTION_LIMIT,
                final_goal=self.target, crafted=False, new_recipe_names=[], station_updates=[], actions=[])
            trial = copy.deepcopy(self); trial.intent19 = intent
            if trial._intent_done(intent):
                record['reason'] = 'completion_already_satisfied'
            else:
                action = trial._intent_step()
                if action:
                    self.intent19 = intent
                    record.update(accepted=True, reason='public_entry_supported_bounded_hypothesis' if exploratory else 'known_task_dependency',
                                  first_action=action, intent_id=intent['id'])
                else:
                    record['reason'] = 'no_admissible_entry_or_known_conditions_blocked'
                    record['blocker'] = trial.blocker19
        self.acceptance19.append(record)
        return record

    def _reliable_fifo(self, trial, action):
        p, t = parse_action(action or ''), trial.table
        if not self._usable(action) or p.verb == 'wait':
            return False
        related = self.needed() | set(trial.queue)
        if trial.active_precondition19 and trial.active_precondition19.get('selected_action') == action:
            return True
        if p.verb == 'craft':
            return p.target in related and bool(t.recipes.get(p.target, {}).get('ingredients'))
        if p.verb in ('pick up','store','take out','drop','equip','unequip'):
            return p.target in related or p.target in t.containers or bool(trial.last_choice.get('structured_action') == action and not trial.explore_pending)
        if p.verb == 'inspect':
            return (p.target in related or p.target == trial.last_produced or p.target == 'inventory'
                    or p.target in t.containers or bool(trial.last_choice.get('structured_action') == action and not trial.explore_pending))
        if p.verb == 'enter':
            return bool(trial.last_choice.get('structured_action') == action and not trial.explore_pending)
        return False

    def _commit(self, trial, action, source):
        before = self
        signature = lambda a: (parse_action(a).verb, parse_action(a).target)
        probe = next((r for r in reversed(trial.probe_candidates19) if signature(r['action']) == signature(action)), None)
        structured = (trial.last_choice or {}).get('structured_action')
        if not structured or signature(structured) != signature(action):
            trial.visits = copy.deepcopy(before.visits)
            if source == 'bounded_S1_fallback_after_planning':
                trial.queue, trial.queue_needs = copy.deepcopy(before.queue), copy.deepcopy(before.queue_needs)
        trial.exploration_spent = before.exploration_spent + int(bool(probe))
        trial.trials, trial.probes = copy.deepcopy(before.trials), copy.deepcopy(before.probes)
        trial.pending_probe = copy.deepcopy(probe['pending']) if probe else None
        trial.explore_pending = copy.deepcopy(probe['exploration']) if probe else None
        if trial.pending_probe:
            trial.pending_probe['action'] = action
        if trial.explore_pending:
            trial.explore_pending['spent'] = trial.exploration_spent
        if probe:
            p = parse_action(action)
            if p.verb == 'inspect':
                trial.probes[p.target] = dict(step=trial.table.state.get('step'), location=trial.table.state.get('location'))
            elif p.verb == 'craft':
                trial.trials[p.target] = before.trials.get(p.target, 0)+1
        trial.audit19 = dict(source=source, final_action=action, assessment=trial.assess(action),
            accepted_intent=copy.deepcopy(trial.intent19), prerequisite=copy.deepcopy(trial.active_precondition19),
            blocker=copy.deepcopy(trial.blocker19), acquisition=copy.deepcopy(trial.acquisitions19),
            transaction=dict(exploration_before=before.exploration_spent, exploration_after=trial.exploration_spent,
                executed_probe=probe, discarded_probes=len(trial.probe_candidates19)-int(bool(probe)),
                failures_unchanged=trial.failures10 == before.failures10,
                attempts_unchanged=len(trial.attempt_log) == len(before.attempt_log)),
            original_task=trial.target, internal_horizon=100)
        trial.last_choice = dict(action=action, reason=source, queue=list(trial.queue), target=trial.target)
        self.__dict__ = copy.deepcopy(trial.__dict__)
        return action

    def choose(self, obs, allow_fallback=False):
        self.table.observe(obs)
        self.condition_log, self.decision10, self.selected_meta = [], {}, None
        self.probe_candidates19, self.acquisitions19, self.mechanism_decision = [], [], {}
        self.active_precondition19 = None
        # P3 can preempt an intent only for publicly supported final progress.
        trial = copy.deepcopy(self)
        final, meta = trial.finish('wait')
        if final and trial._usable(final):
            if trial.intent19:
                trial.close_intent('cancelled', 'P3_public_final_task_progress')
            return self._commit(trial, final, 'P3_finish')
        if self.intent19:
            trial = copy.deepcopy(self); action = trial._intent_step()
            if action:
                return self._commit(trial, action, 'persistent_subgoal')
            # Commit the lifecycle transition, never a discarded probe/queue.
            self.intent19, self.intent_log19 = trial.intent19, trial.intent_log19
            self.blocker19 = trial.blocker19
        # Workstations / other missing area objects are public prerequisites.
        for product in dict.fromkeys(self.queue + [parse_action(self.target).target] + sorted(self.needed())):
            if any(not (self.table.state.get('ground') or {}).get(n, 0)
                   for n in self.table.recipes.get(product, {}).get('stations', [])):
                trial = copy.deepcopy(self); action = trial._station(product)
                if trial._usable(action):
                    return self._commit(trial, action, 'public_prerequisite')
                self.blocker19 = trial.blocker19 or dict(kind='unknown_precondition_path', item=product)
        trial = copy.deepcopy(self)
        action = Budget100Controller.choose(trial, obs, 'wait')
        action = trial._bound(action, source='final_FIFO_candidate')
        if trial._reliable_fifo(trial, action):
            return self._commit(trial, action, 'known_FIFO_execution')
        if not self.blocker19:
            goal = parse_action(self.target).target
            missing = sorted(n for n in self.needed() if not self.table.recipes.get(n, {}).get('ingredients')
                             and (n == goal or self.ownership(n)['lower_bound'] == 0))
            self.blocker19 = dict(kind='public_knowledge_gap' if missing else 'FIFO_no_reliable_progress',
                                  item=missing[0] if missing else goal, unresolved=missing)
        if allow_fallback:
            if action and action != 'wait' and trial._usable(action):
                return self._commit(trial, action, 'bounded_S1_fallback_after_planning')
            return self._commit(copy.deepcopy(self), 'wait', 'no_admissible_public_action')
        return None

    def observe(self, before, action, after):
        old_recipes = set(self.table.recipes)
        old_conditions = {n: set(r.get('stations', [])) for n, r in self.table.recipes.items()}
        active_id = self.intent19['id'] if self.intent19 else None
        super().observe(before, action, after)  # exactly one inherited feedback update
        feedback = self.table.state['feedback']; p = parse_action(action)
        new_recipes = sorted(set(self.table.recipes) - old_recipes)
        new_conditions = []
        for product, recipe in self.table.recipes.items():
            for item in recipe.get('stations', []):
                key = product + ':' + item
                if item not in old_conditions.get(product, set()):
                    record = dict(product=product, required_object=item, object_type='UNKNOWN',
                        first_step=self.step16, native_step=after['step'], raw_feedback=feedback,
                        evidence_ids=recipe.get('evidence_ids', []), first_satisfied_step=None,
                        source='native_missing_necessary_feedback')
                    self.preconditions19.setdefault(key, record)
                    new_conditions.append(key)
                record = self.preconditions19.get(key)
                if record and record['first_satisfied_step'] is None and (self.table.state.get('ground') or {}).get(item, 0):
                    record['first_satisfied_step'] = self.step16
                    self.precondition_events19.append(dict(event='public_precondition_satisfied', key=key,
                        step=self.step16, latency=self.step16-record['first_step'], action=action))
        if self.intent19 and self.intent19['id'] == active_id:
            intent = self.intent19
            intent['steps'] += 1; intent['remaining_actions'] -= 1
            intent['actions'].append(dict(step=self.step16, action=action))
            intent['new_recipe_names'] += new_recipes
            intent['station_updates'] += new_conditions
            if p.verb == 'craft' and p.target == intent['target'] and 'successfully crafted' in feedback:
                intent['crafted'] = True
            if self._intent_done(intent):
                self.close_intent('completed', 'real_public_feedback_satisfies_condition')
            elif re.search(r'Cannot |Invalid ', feedback):
                self.close_intent('failed', 'native_feedback_blocks_current_direction')
            elif self.risk16:
                self.close_intent('cancelled', 'immediate_public_health_or_combat_risk')
            elif intent['remaining_actions'] <= 0:
                self.close_intent('expired', 'fixed_intent_action_limit')
        self.outcome19 = dict(action=action, feedback=feedback, new_recipe_names=new_recipes,
            new_preconditions=new_conditions, public_craft_success='successfully crafted' in feedback,
            active_intent=copy.deepcopy(self.intent19), latest_intent_end=copy.deepcopy(self.intent_log19[-1:]),
            preconditions=copy.deepcopy(self.preconditions19), exploration_spent=self.exploration_spent)
        # Triggers are recomputed from the actual new state on the next choose.
        self.blocker19 = {}

    def to_dict(self):
        return copy.deepcopy(super().to_dict())

    @classmethod
    def from_dict(cls, data):
        obj = cls()
        obj.__dict__.update(BaselineController.from_dict(data).__dict__)
        return obj
