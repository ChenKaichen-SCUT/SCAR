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
from .planning import validate, COMPLETION
from .evidence import check as check_evidence


class Controller20(Budget100Controller):
    def __init__(self):
        super().__init__('S1_P1_P3')
        self.intent20 = None
        self.intent_log20 = []
        self.acceptance20 = []
        self.request_contexts20 = []
        self.plan_calls20 = 0
        self.blocker20 = {}
        self.preconditions20 = {}
        self.precondition_events20 = []
        self.active_precondition20 = None
        self.probe_candidates20 = []
        self.acquisitions20 = []
        self.audit20 = {}
        self.outcome20 = {}
        self.evidence20 = {}
        self.request_evidence20 = []
        self.context_counts20 = {}
        self.lifecycle20 = []
        self.suspended20 = None
        self.recovery20 = {'state':'EXECUTE','reason':None}
        self.recovery_log20 = []
        self.entry_attempts20 = {}
        self.last_plan20 = None
        self.observation_count20 = 0

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
        if self.intent20:
            nodes |= self._all_needed(self.intent20['target'])
        return nodes

    def assess(self, action):
        return assess(self, action)

    def _bound(self, action, **kwargs):
        if not action:
            return None
        action, record = bound_store(self, action, **kwargs)
        if record:
            self.acquisitions20.append(record)
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
            self.probe_candidates20.append(dict(action=result, pending=copy.deepcopy(self.pending_probe),
                                                exploration=copy.deepcopy(self.explore_pending)))
        return result

    def _usable(self, action):
        return bool(action and self.assess(action)['status'] != 'REJECT'
                    and self.actual_visits.get(digest([action, self.context(action)]), 0) < 2)

    def block(self, kind, item, **extra):
        self.blocker20 = dict(kind=kind, item=item, **extra)
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
            return self.block('missing_area_object_path' if ground else 'missing_material_path' if ancestors else 'missing_target_recipe', item, requires_ground=ground, parent=ancestors[-1] if ancestors else None, chain=list(ancestors), current_required_action='craft 1 '+q(ancestors[-1] if ancestors else item))
        for dep in ingredients:
            required = (recipe.get('quantities') or {}).get(dep, self.quotas.get(item, 1))
            if self.ownership(dep)['lower_bound'] < required:
                self.queue_needs[dep] = max(self.queue_needs.get(dep, 1), required)
                return self.known_step(dep, required, ancestors + (item,))
        for requirement in recipe.get('stations', []):
            if not (t.state.get('ground') or {}).get(requirement, 0):
                self.active_precondition20 = dict(product=item, required_object=requirement,
                    object_type='UNKNOWN', evidence_ids=recipe.get('evidence_ids', []), chain=list(ancestors))
                return self.known_step(requirement, 1, ancestors + (item,), ground=True)
        candidate = self._batch_action('craft 1 ' + q(item))
        if self._usable(candidate):
            return candidate
        return self.block('known_execution_conditions_blocked', item, assessment=self.assess(candidate))

    def _station(self, product):
        t = self.table
        if self.ownership(product)['lower_bound'] >= self.queue_needs.get(product,1):return None
        for item in t.recipes.get(product, {}).get('stations', []):
            if not (t.state.get('ground') or {}).get(item, 0):
                self.active_precondition20 = dict(product=product, required_object=item,
                    object_type='UNKNOWN', evidence_ids=t.recipes[product].get('evidence_ids', []))
                action = self.known_step(item, 1, (product,), ground=True)
                if action and self.active_precondition20:
                    self.active_precondition20['selected_action'] = action
                return action
        return None

    def planning_context(self):
        t=self.table
        return digest(dict(resources=self._signature(),
            recipes={n:{k:r.get(k) for k in ('ingredients','quantities','stations')} for n,r in t.recipes.items()},
            inspected=sorted(t.inspected),links=t.links,guards=t.guards,
            blocker={k:self.blocker20.get(k) for k in ('kind','item','parent','requires_ground')},risk=self.risk16))

    def recovery(self,state,reason,**extra):
        self.recovery20=dict(state=state,reason=reason,step=self.step16,**extra)
        if not self.recovery_log20 or self.recovery_log20[-1]!=self.recovery20:
            self.recovery_log20.append(copy.deepcopy(self.recovery20))

    def can_request(self):
        return self.plan_calls20<MAX_PLANNING_CALLS and self.context_counts20.get(self.planning_context(),0)<2

    def start_request(self):
        context=self.planning_context();count=self.context_counts20.get(context,0)
        self.plan_calls20+=1;self.context_counts20[context]=count+1;self.request_contexts20.append(context)
        self.recovery('REPLAN' if count else 'PLAN','same_public_context_retry' if count else 'new_public_context',
            context=context,context_attempt=count+1,global_calls=self.plan_calls20)

    def planning_failed(self,reason):
        self.last_plan20=dict(status='interface_unavailable',reason=reason,step=self.step16)
        self.recovery('FALLBACK','three_audited_responses_unusable')

    def _known_path(self,item,ancestors=()):
        if item in ancestors or len(ancestors)>=PRECONDITION_DEPTH_LIMIT:return False
        if self.ownership(item)['lower_bound']>0 or (self.table.state.get('ground') or {}).get(item,0) or self.locations(item):return True
        rule=self.table.recipes.get(item,{})
        return bool(rule.get('ingredients') and all(self._known_path(n,ancestors+(item,))
            for n in rule['ingredients']+rule.get('stations',[])))

    def _intent_done(self,intent):
        kind,item,t=intent['type'],intent['target'],self.table
        if kind=='INSPECT_OBJECT':return item in t.inspected
        if kind=='EXPLORE_FRONTIER':return item==t.state.get('location')
        if kind=='LOCATE_PRECONDITION':return self._known_path(item)
        if kind=='CRAFT_PRECONDITION' and intent.get('crafted'):return True
        return self.ownership(item)['lower_bound']>=intent.get('amount',1)

    def close_intent(self,status,reason):
        if self.intent20:
            self.lifecycle20.append(dict(id=self.intent20['id'],event=status,reason=reason,step=self.step16,
                steps=self.intent20['steps'],target=self.intent20['target']))
        super_close(self,status,reason)

    def suspend_intent(self,reason):
        if not self.intent20:return
        self.intent20['status']='blocked';self.intent20['blocked_context']=self.planning_context()
        self.lifecycle20.append(dict(id=self.intent20['id'],event='blocked',reason=reason,step=self.step16))
        self.suspended20=copy.deepcopy(self.intent20);self.intent20=None

    def _inspect_entry(self,item):
        if item in self.visible() or item=='inventory' and self.table.inventory:return 'inspect '+q(item)
        for location in self.locations(item):
            if action:=self._move(location):return action
        return self.block('inspection_entry_no_longer_accessible',item)

    def _entry_step(self,intent):
        entry=intent['entry'];t=self.table
        destinations=set(self.public_entries()['reachable'])|{t.state.get('location')}
        if entry in destinations:
            if entry!=t.state.get('location'):return self._move(entry)
        elif entry not in t.inspected:return self._inspect_entry(entry)
        # Continue the same bounded search after arrival/inspection. A public
        # intermediate recipe may be inspected, but no hidden chain is assumed.
        for name in sorted(self.visible()):
            if name not in t.inspected and self._usable('inspect '+q(name)):return 'inspect '+q(name)
        return None

    def _intent_step(self):
        intent=self.intent20
        if self._intent_done(intent):self.close_intent('completed','real_public_completion');return None
        if intent['remaining_actions']<=0:self.close_intent('expired','fixed_intent_action_limit');return None
        kind,item=intent['type'],intent['target'];exploratory=False
        if kind in ('ACQUIRE_MATERIAL','CRAFT_PRECONDITION'):
            action=self.known_step(item,intent['amount'])
            if not action and kind=='ACQUIRE_MATERIAL':action=self._entry_step(intent);exploratory=bool(action)
        elif kind=='INSPECT_OBJECT':action=self._inspect_entry(item);exploratory=True
        elif kind=='EXPLORE_FRONTIER':action=self._move(item);exploratory=True
        else:action=self._entry_step(intent);exploratory=True
        if not self._usable(action):self.suspend_intent('no_current_admissible_entry_or_dependency');return None
        if exploratory:
            action=self._probe(action,'accepted_bounded_subgoal',{'intent_id':intent['id'],'type':kind})
            if not action:self.close_intent('expired','inherited_exploration_budget_exhausted')
        return action

    def accept(self,proposal,prompt=None):
        validate(proposal);t=self.table;kind,item,entry=(proposal[k] for k in ('type','target','entry'))
        entries=self.public_entries();public=set(entries['visible'])|set(t.recipes)|self.needed()
        for data in t.places.values():public.update(data['objects'])
        for r in t.recipes.values():public.update(r.get('ingredients',[])+r.get('stations',[]))
        destinations=set(entries['reachable'])|{t.state.get('location')}
        key=digest([kind,item,entry,self.planning_context()]);reason,refs=check_evidence(self,proposal)
        if self.intent20:reason=reason or 'unfinished_intent_conflict'
        if entry not in public|destinations|({'inventory'} if t.inventory else set()):reason=reason or 'no_public_execution_entry'
        if item not in public|destinations:reason=reason or 'target_not_publicly_named'
        if any(a['key']==key for a in self.acceptance20):reason=reason or 'duplicate_subgoal_same_conditions'
        if kind=='EXPLORE_FRONTIER' and item not in destinations:reason=reason or 'no_public_route'
        if kind=='INSPECT_OBJECT' and item in t.inspected:reason=reason or 'already_inspected'
        if kind=='CRAFT_PRECONDITION' and not t.recipes.get(item,{}).get('ingredients'):
            reason=reason or 'recipe_unpublished_not_an_executable_craft_intent'
        related=item in self.needed() or item==self.blocker20.get('item')
        if kind in ('ACQUIRE_MATERIAL','CRAFT_PRECONDITION','LOCATE_PRECONDITION') and not related:
            reason=reason or 'not_a_current_dependency_or_blocker'
        exploratory=kind in ('INSPECT_OBJECT','EXPLORE_FRONTIER','LOCATE_PRECONDITION') or not self._known_path(item)
        if exploratory and self.exploration_spent>=self.EXPLORATION_LIMIT:reason=reason or 'inherited_exploration_budget_exhausted'
        record=dict(key=key,proposal=copy.deepcopy(proposal),accepted=False,reason=reason,step=self.step16,
            evidence_refs=copy.deepcopy(refs),validation_layer='evidence_or_decision',
            context=self.planning_context(),evidence_scope='public entry only; hypotheses never promoted')
        if reason is None:
            amount=self.amount if item==parse_action(self.target).target else self.queue_needs.get(item,1)
            # Public nominal demand only; do not add new batching/rounding rules.
            from .acquisition import public_demand
            demand,_,_=public_demand(self,item)
            if demand is not None:amount=demand
            intent=dict(copy.deepcopy(proposal),id='sg20_'+str(len(self.acceptance20)+1),completion=COMPLETION[kind],
                status='active',start_step=self.step16,steps=0,amount=amount,exploratory=exploratory,
                remaining_actions=EXPLORATORY_ACTION_LIMIT if exploratory else INTENT_ACTION_LIMIT,
                final_goal=self.target,crafted=False,new_recipe_names=[],station_updates=[],actions=[],resumes=0)
            trial=copy.deepcopy(self);trial.intent20=intent
            if trial._intent_done(intent):record['reason']='completion_already_satisfied'
            elif action:=trial._intent_step():
                if self.suspended20:
                    self.intent20=self.suspended20;self.suspended20=None
                    self.close_intent('cancelled','replaced_by_new_verified_subgoal')
                self.intent20=intent
                self.lifecycle20.append(dict(id=intent['id'],event='accepted',step=self.step16,first_action=action))
                record.update(accepted=True,reason='public_entry_supported_bounded_hypothesis' if exploratory else 'known_task_dependency',
                    first_action=action,intent_id=intent['id'])
            else:record.update(reason='no_admissible_entry_or_known_conditions_blocked',blocker=trial.blocker20)
        self.acceptance20.append(record);self.last_plan20=copy.deepcopy(record)
        return record

    def exploration_entry(self):
        if self.exploration_spent>=self.EXPLORATION_LIMIT:return None
        t=self.table
        # A bounded fallback over native visible objects and public neighbors;
        # no model semantic ranking and no task-specific identifiers.
        candidates=['inspect '+q(n) for n in sorted(self.visible()) if n not in t.inspected]
        candidates += ['enter '+q(n) for n in sorted(t.state.get('neighbors') or [])
            if n not in t.places or any(o not in t.inspected for o in t.places[n]['objects'])]
        for action in candidates:
            key=digest([action,self.context(action)])
            if self.entry_attempts20.get(key,0)==0 and self._usable(action):
                return self._probe(action,'bounded_public_recovery_entry',{'blocker':self.blocker20,'entry_key':key})
        return None

    def _reliable_fifo(self, trial, action):
        p, t = parse_action(action or ''), trial.table
        if not self._usable(action) or p.verb == 'wait':
            return False
        related = self.needed() | set(trial.queue)
        if trial.active_precondition20 and trial.active_precondition20.get('selected_action') == action:
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
        probe = next((r for r in reversed(trial.probe_candidates20) if signature(r['action']) == signature(action)), None)
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
        trial.audit20 = dict(source=source, final_action=action, assessment=trial.assess(action),
            accepted_intent=copy.deepcopy(trial.intent20), prerequisite=copy.deepcopy(trial.active_precondition20),
            blocker=copy.deepcopy(trial.blocker20), acquisition=copy.deepcopy(trial.acquisitions20),
            transaction=dict(exploration_before=before.exploration_spent, exploration_after=trial.exploration_spent,
                executed_probe=probe, discarded_probes=len(trial.probe_candidates20)-int(bool(probe)),
                failures_unchanged=trial.failures10 == before.failures10,
                attempts_unchanged=len(trial.attempt_log) == len(before.attempt_log)),
            original_task=trial.target, internal_horizon=100)
        trial.last_choice = dict(action=action, reason=source, queue=list(trial.queue), target=trial.target)
        self.__dict__ = copy.deepcopy(trial.__dict__)
        return action

    def choose(self,obs,allow_fallback=False):
        self.table.observe(obs)
        self.condition_log,self.decision10,self.selected_meta=[],{},None
        self.probe_candidates20,self.acquisitions20,self.mechanism_decision=[],[],{}
        self.active_precondition20=None;self.blocker20={}
        trial=copy.deepcopy(self);final,meta=trial.finish('wait')
        if final and trial._usable(final):
            if (trial.intent20 and parse_action(final).target==trial.intent20['target']
                    and trial.intent20['type'] in ('ACQUIRE_MATERIAL','CRAFT_PRECONDITION')):
                continuing=copy.deepcopy(self);next_action=continuing._intent_step()
                if next_action==final:return self._commit(continuing,final,'persistent_subgoal')
            if trial.intent20:trial.close_intent('cancelled','P3_public_final_task_progress')
            return self._commit(trial,final,'P3_finish')
        if self.suspended20 and self.suspended20.get('resumes',0)<2:
            trial=copy.deepcopy(self);trial.intent20=trial.suspended20;trial.suspended20=None
            action=trial._intent_step()
            if action:
                trial.intent20['status']='active';trial.intent20['resumes']+=1
                trial.lifecycle20.append(dict(id=trial.intent20['id'],event='resumed',step=self.step16))
                return self._commit(trial,action,'persistent_subgoal')
        if self.intent20:
            trial=copy.deepcopy(self);action=trial._intent_step()
            if action:return self._commit(trial,action,'persistent_subgoal')
            for field in ('intent20','intent_log20','suspended20','lifecycle20','blocker20'):
                setattr(self,field,copy.deepcopy(getattr(trial,field)))
        trial=copy.deepcopy(self);action=Budget100Controller.choose(trial,obs,'wait')
        action=trial._bound(action,source='final_FIFO_candidate')
        if trial._reliable_fifo(trial,action):return self._commit(trial,action,'known_FIFO_execution')
        # Resolve only the current unfinished goal chain, not every historical
        # station requirement of an already-owned intermediate.
        known=copy.deepcopy(self);goal=parse_action(self.target).target
        candidate=known.known_step(goal,self.amount)
        if known._usable(candidate):return self._commit(known,candidate,'public_dependency_execution')
        self.blocker20=known.blocker20 or dict(kind='known_execution_blocked',item=goal)
        self.blocker20.setdefault('current_required_action','craft 1 '+goal)
        self.blocker20['public_entries']=self.public_entries()
        self.recovery('BLOCKED','no_reliable_known_action',blocker=copy.deepcopy(self.blocker20))
        if allow_fallback:
            fallback=copy.deepcopy(self);candidate=fallback.exploration_entry()
            if candidate:
                fallback.recovery('EXPLORE','untried_public_entry')
                return self._commit(fallback,candidate,'bounded_public_recovery')
            self.recovery('REPLAN' if self.can_request() else 'STALLED',
                'bounded_replanning_available' if self.can_request() else 'public_entries_and_replanning_exhausted')
        return None

    def observe(self, before, action, after):
        old_recipes = set(self.table.recipes)
        old_conditions = {n: set(r.get('stations', [])) for n, r in self.table.recipes.items()}
        active_id = self.intent20['id'] if self.intent20 else None
        key=digest([action,self.context(action)])
        super().observe(before, action, after)  # exactly one inherited feedback update
        self.observation_count20 += 1
        self.entry_attempts20[key]=self.entry_attempts20.get(key,0)+1
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
                    self.preconditions20.setdefault(key, record)
                    new_conditions.append(key)
                record = self.preconditions20.get(key)
                if record and record['first_satisfied_step'] is None and (self.table.state.get('ground') or {}).get(item, 0):
                    record['first_satisfied_step'] = self.step16
                    self.precondition_events20.append(dict(event='public_precondition_satisfied', key=key,
                        step=self.step16, latency=self.step16-record['first_step'], action=action))
        if self.intent20 and self.intent20['id'] == active_id:
            intent = self.intent20
            intent['steps'] += 1; intent['remaining_actions'] -= 1
            intent['actions'].append(dict(step=self.step16, action=action))
            intent['new_recipe_names'] += new_recipes
            intent['station_updates'] += new_conditions
            if p.verb == 'craft' and p.target == intent['target'] and 'successfully crafted' in feedback:
                intent['crafted'] = True
            if self._intent_done(intent):
                self.close_intent('completed', 'real_public_feedback_satisfies_condition')
            elif re.search(r'Cannot |Invalid ', feedback):
                self.lifecycle20.append(dict(id=intent['id'],event='execution_blocked',step=self.step16,feedback=feedback))
            elif self.risk16:
                self.close_intent('cancelled', 'immediate_public_health_or_combat_risk')
            elif intent['remaining_actions'] <= 0:
                self.close_intent('expired', 'fixed_intent_action_limit')
        self.outcome20 = dict(action=action, feedback=feedback, new_recipe_names=new_recipes,
            new_preconditions=new_conditions, public_craft_success='successfully crafted' in feedback,
            active_intent=copy.deepcopy(self.intent20), latest_intent_end=copy.deepcopy(self.intent_log20[-1:]),
            preconditions=copy.deepcopy(self.preconditions20), exploration_spent=self.exploration_spent,
            lifecycle=copy.deepcopy(self.lifecycle20),suspended_intent=copy.deepcopy(self.suspended20),recovery=copy.deepcopy(self.recovery20))
        # Triggers are recomputed from the actual new state on the next choose.
        self.blocker20 = {}

    def to_dict(self):
        return copy.deepcopy(super().to_dict())

    @classmethod
    def from_dict(cls, data):
        obj = cls()
        obj.__dict__.update(BaselineController.from_dict(data).__dict__)
        return obj


def super_close(self,status,reason):
    if not self.intent20:return
    self.intent_log20.append(dict(copy.deepcopy(self.intent20),status=status,end_step=self.step16,
        termination_reason=reason,final_goal_unchanged=self.target==self.intent20['final_goal']))
    self.intent20=None
