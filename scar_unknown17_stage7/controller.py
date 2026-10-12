"""Four opt-in mechanisms. Policy inputs are exclusively observed public facts.

All switches off delegates verbatim to frozen Stage 6. No environment or evaluator
imports, per-item rules, or undisclosed quantity assumptions are permitted here.
"""
import copy
import math
import re
from scar.io import digest
from scar_sequence.planner import q
from scar_sequence.public import ResourceTable
from scar_unknown17.controller import SimpleController
from scar_unknown17.facts import PublicFacts, carried_counts
from scar_v3.state import parse_action

FLAGS = ('retry_context_fix', 'knowledge_gap_exploration',
         'explore_execute_switch', 'resource_goal_guard')
CONFIGS = {f'C{i}': dict(zip(FLAGS, bits)) for i,bits in enumerate([
    (False,False,False,False), (True,False,False,False), (False,True,False,False),
    (False,False,True,False), (False,False,False,True), (True,True,True,True)])}


class Stage7Controller(SimpleController):
    def __init__(self, retry_context_fix=False, knowledge_gap_exploration=False,
                 explore_execute_switch=False, resource_goal_guard=False):
        super().__init__(True, 'learned')
        self.flags = dict(zip(FLAGS, (retry_context_fix, knowledge_gap_exploration,
                                    explore_execute_switch, resource_goal_guard)))
        self.retry_records = {}; self.attempt_log = []; self.pending_probe = None
        self.gap = {}; self.gap_log = []
        self.execution_mode = 'EXPLORE'; self.mode_signature = None; self.subgoals = {}
        self.mode_log = []; self.blocked_execution = None
        self.stage7_decision = {}; self.last_ready = []; self.public_quantity_rules = {}

    def enabled(self, name):
        return self.flags[name]

    def public_context(self, item):
        t=self.table; r=t.recipes.get(item,{})
        return {'location':t.state.get('location'),
            'stations':{s:(t.state.get('ground') or {}).get(s,0)>0 for s in r.get('stations',[])},
            'materials':{x:t.count(x) for x in r.get('ingredients',[])},
            'visible':item in self.visible()}

    def visible(self):
        t=self.table; s=t.state
        names=set(s.get('ground') or {})|set(s.get('hands') or {})|set(s.get('equipment') or {})
        for c,data in t.containers.items():
            if t.carried(c):names.update(data['counts'] or {})
        return names

    def retry_allowed(self, action):
        p=parse_action(action); record=self.retry_records.get(p.verb+':'+p.target)
        if not record:return True
        if record['state']=='TESTED_WITH_RELEVANT_CONDITIONS' and 'Cannot ' in record['feedback']:
            now=self.public_context(p.target);before=record['context']
            return (now['materials'],now['stations'],now['visible']) != (before['materials'],before['stations'],before['visible'])
        if record['state']!='BLOCKED_BY_PRECONDITION':return True
        now=self.public_context(p.target); before=record['context']; failure=record['failure_type']
        if failure=='station':
            return bool(now['stations']) and all(now['stations'].values()) and not all(before['stations'].values())
        if failure=='materials':
            return any(v is not None and (before['materials'].get(x) is None or v>before['materials'][x])
                       for x,v in now['materials'].items())
        if failure=='not_accessible':return now['visible'] and not before['visible']
        # An unclassified failure is scoped to relevant conditions, not elapsed time.
        return (now['materials'],now['stations'],now['visible']) != (before['materials'],before['stations'],before['visible'])

    def _probe(self, action, reason, source):
        p=parse_action(action)
        if self.enabled('retry_context_fix') and not self.retry_allowed(action):
            self.stage7_decision.setdefault('A_suppressed',[]).append({'action':action,'reason':'failed precondition unchanged'})
            return None
        result=super()._probe(action,reason,source)
        self.pending_probe={'action':action,'context':self.public_context(p.target),
            'reason':reason,'source':copy.deepcopy(source),'gap':copy.deepcopy(self.gap),
            'classification':'information_inspection' if p.verb=='inspect' else
                'preparation_transport' if p.verb in {'store','take out','pick up','enter','equip','drop'} else
                'forward_production_with_delayed_information_value',
            'expected_information':'downstream recipe names' if p.verb in {'inspect','craft'} else 'access to inspectable materials',
            'step':self.table.state.get('step')}
        if self.enabled('knowledge_gap_exploration'):
            self.stage7_decision['B_selection']=copy.deepcopy(self.pending_probe)
        return result

    def update_gap(self):
        goal=parse_action(self.target).target; relevant=self._all_needed(goal)
        missing=sorted(x for x in relevant if not self.table.recipes.get(x,{}).get('ingredients')
                       and (x==goal or (self.table.count(x) or 0)<1))
        new={'goal':goal,'known_dependency_nodes':sorted(relevant),'unresolved_nodes':missing,
             'kind':'missing_goal_connection' if goal in missing else 'missing_upstream_or_quantity_conditions',
             'scope':'absent recipe is UNKNOWN; a node may be a raw material, not necessarily craftable'}
        if new!=self.gap:
            self.gap_log.append({'step':self.table.state.get('step'),'previous':self.gap,'current':copy.deepcopy(new)})
        self.gap=new
        return relevant

    def _gap_explore(self, needed):
        if self.exploration_spent>=self.EXPLORATION_LIMIT:return None
        t=self.table; s=t.state; goal=parse_action(self.target).target
        relevant=self.update_gap(); visible=self.visible()
        stations={x for r in t.recipes.values() for x in r.get('stations',[])}
        sources={x for r in t.recipes.values() for x in r.get('ingredients',[])}
        def rank(item):
            return (0 if item in relevant else 1 if item==self.last_produced else
                    2 if item not in stations and item not in t.containers else 4, item)
        candidates=sorted((x for x in visible if x not in t.inspected and x not in self.probes),key=rank)
        for item in candidates:
            if rank(item)[0]>2:continue
            self.probes[item]={'step':s.get('step'),'location':s.get('location')}
            return self._probe('inspect '+q(item),'inspect public object at active knowledge gap',
                {'public_entity':item,'priority':rank(item)[0], 'known_material_source':item in sources})
        supplies=set(visible)
        for data in t.places.values():supplies.update(data['objects'])
        products=[]
        for product,r in t.recipes.items():
            deps=r.get('ingredients',[])
            if not deps or product==goal or self.trials.get(product,0)>=1:continue
            if not all(x in supplies or (t.count(x) or 0)>0 for x in deps):continue
            if (t.count(product) or 0)>0 or any(d['objects'].get(product,0)>0 for d in t.places.values()):continue
            # A product made FROM the held goal is a downstream detour, not a bridge
            # to that missing goal. Rank it last, without permanently banning it.
            products.append((goal in deps, product not in relevant,
                             -len(set(product.split('_'))&set(goal.split('_'))),len(deps),product))
        if sum(self.trials.values())<self.TRIAL_LIMIT and products:
            product=min(products)[-1]; r=t.recipes[product]
            for dep in r['ingredients']:
                if (t.count(dep) or 0)<1:
                    a=self._acquire(dep,1,set(needed)|set(r['ingredients']))
                    return self._probe(a,'prepare material for gap bridge',{'product':product,'ingredient':dep}) if a else None
            if a:=self._station(product):return self._probe(a,'reach station for gap bridge',{'product':product})
            self.trials[product]=self.trials.get(product,0)+1
            return self._probe('craft 1 '+q(product),'bounded forward recipe trial',{'recipe':product,'observed':r})
        # Broad exploration remains available; no immediate gain is not a ban.
        return super()._explore(needed)

    def _explore(self, needed):
        if self.enabled('retry_context_fix'):
            for key,record in self.retry_records.items():
                if record['state']!='BLOCKED_BY_PRECONDITION':continue
                p=parse_action(record['action'])
                if p.verb=='craft' and record['was_forward_trial']:
                    # Permit travel/preparation without charging an effective trial.
                    # _probe still requires actual condition release before crafting.
                    if record['failure_type'] in {'station','materials'}:self.trials[p.target]=0
                elif p.verb=='inspect' and self.retry_allowed(record['action']):
                    self.probes.pop(p.target,None)
        return self._gap_explore(needed) if self.enabled('knowledge_gap_exploration') else super()._explore(needed)

    def ready_nodes(self):
        t=self.table; goal=parse_action(self.target).target; nodes=list(dict.fromkeys(self.queue+[goal]))
        ready=[]
        for item in nodes:
            r=t.recipes.get(item,{}); deps=r.get('ingredients',[]); stations=r.get('stations')
            need=self.amount if item==goal else self.queue_needs.get(item,1)
            if (t.count(item) or 0)>=need or not deps:continue
            quota=self.quotas.get(item,1)
            if not all((t.count(x) or 0)>=(r.get('quantities') or {}).get(x,quota) for x in deps):continue
            if not stations or not all((t.state.get('ground') or {}).get(x,0)>0 for x in stations):continue
            if self.blocked_execution and self.blocked_execution['node']==item:continue
            ready.append(item)
        return ready

    def _fifo(self,item):
        if not self.enabled('explore_execute_switch'):return super()._fifo(item)
        if not self.queue:self.queue=[item]
        # Retain FIFO worklist; append newly disclosed missing dependencies only.
        for head in list(self.queue):
            r=self.table.recipes.get(head,{})
            for dep in r.get('ingredients',[]):
                required=(r.get('quantities') or {}).get(dep,self.quotas.get(head,1))
                if (self.table.count(dep) or 0)<required:
                    self.queue_needs[dep]=max(self.queue_needs.get(dep,1),required)
                    if dep not in self.queue:self.queue.append(dep)
        self.last_ready=self.ready_nodes()
        if self.last_ready:
            node=self.last_ready[0];a='craft 1 '+q(node)
            self.subgoals.setdefault(node,{})['next_action']=a
            self.stage7_decision['C_ready_execution']={'node':node,'ready':list(self.last_ready),
                'basis':'public material lower bounds and observed station; quantity samples remain conditional'}
            return a
        action=super()._fifo(item)
        if self.blocked_execution and action and parse_action(action).verb=='craft' and parse_action(action).target==self.blocked_execution['node']:
            node=self.blocked_execution['node']
            return self._explore({node}|set(self.table.recipes.get(node,{}).get('ingredients',[])))
        return action

    def _set_mode(self,action):
        p=parse_action(action); relevant=self._all_needed(parse_action(self.target).target)
        if self.blocked_execution:
            want='RECOVER';reason='new public execution failure requires local repair'
        elif self.stage7_decision.get('C_ready_execution') or (p.target in relevant and p.verb in {'craft','store','pick up','take out'}):
            want='EXECUTE';reason='known queue subgoal has a public next action'
        elif self.explore_pending or p.verb=='inspect':
            want='EXPLORE';reason='resolve an explicit unknown condition or recipe connection'
        else:want=self.execution_mode;reason='retain mode and valid FIFO worklist'
        signature=digest([self._signature(),{k:{f:r.get(f) for f in ['ingredients','stations','quantities']} for k,r in self.table.recipes.items()}])
        if want!=self.execution_mode and signature!=self.mode_signature:
            event={'event':'stage7_mode_transition','old':self.execution_mode,'new':want,
                   'reason':reason,'public_signature':signature,'step':self.table.state.get('step')}
            self.mode_log.append(event);self.events.append(event);self.execution_mode=want;self.mode_signature=signature
        self.stage7_decision['C_mode']={'mode':self.execution_mode,'reason':reason,
            'ready':self.last_ready,'subgoals':copy.deepcopy(self.subgoals),'blocked':copy.deepcopy(self.blocked_execution)}

    def _goal_action(self,base):
        t=self.table; goal=parse_action(self.target).target; own=t.count(goal)
        if own is not None and own>=self.amount:
            if parse_action(base).verb=='craft':return 'wait','public_goal_already_complete'
            return base,'public_goal_already_complete'
        ground=t.state.get('ground') or {}; hands=t.state.get('hands') or {}
        if ground.get(goal,0)>0:
            # Pickup adds a ground copy, unlike storing the already-held copy.
            if sum(hands.values())<2:
                a='pick up '+q(goal)
                return (base if parse_action(base).verb=='pick up' and parse_action(base).target==goal else a),'visible_final_copy_pickup'
            if t.inventory:
                c=t.containers.get(t.inventory,{})
                n=int(hands.get(goal,0)+min(ground[goal],max(1,self.amount-(own or 0))))
                load,cap=c.get('load'),c.get('capacity')
                if cap is not None and load is not None and cap-load>=n:
                    a=f'store {n} {q(goal)} inventory'
                    b=parse_action(base)
                    if b.verb=='store' and b.target==goal and int(b.args[0])>=n and b.args[-1]=='inventory':a=base
                    return a,'store_including_held_copy_then_visible_final_copy'
                # Known held copy can be stored to free a hand, even if current
                # capacity is not certified. This is preparation, not immediate proof.
                if hands.get(goal,0)>0 and (load is None or cap is None or cap-load>=1):
                    return f'store 1 {q(goal)} inventory','free_hand_for_visible_final_copy_capacity_uncertain'
        for name,c in sorted(t.containers.items()):
            if not t.carried(name) and t.access(name) and (c.get('counts') or {}).get(goal,0)>0 and sum(hands.values())<2:
                return f'take out {q(goal)} {q(name)}','take_visible_final_copy_from_accessible_container'
        return None,None

    def public_demand(self,target):
        goal=parse_action(self.target).target
        demand=self.amount if target==goal else self.queue_needs.get(target,1)
        for parent in self._all_needed(goal)-{target}:
            need=self.amount if parent==goal else self.queue_needs.get(parent,1)
            missing=max(0,need-(self.table.count(parent) or 0))
            qty=self.public_quantity_rules.get(parent,{}).get('quantities',{}).get(target)
            if qty is not None and missing>0:demand=max(demand,math.ceil(qty*missing))
        return demand

    def reservations(self,target):
        goal=parse_action(self.target).target; relevant=self._all_needed(goal); reserved={}
        for item in sorted(relevant-{target}):
            need=self.amount if item==goal else self.queue_needs.get(item,1)
            if (self.table.count(item) or 0)>=need:continue
            for dep in self.table.recipes.get(item,{}).get('ingredients',[]):
                if dep==target:continue
                # Names imply presence requirements, NOT a linear weight. One is
                # a conservative planning floor; exact future quantities UNKNOWN.
                qty=self.public_quantity_rules.get(item,{}).get('quantities',{}).get(dep,1)
                reserved[dep]=max(reserved.get(dep,0),qty*max(1,need-(self.table.count(item) or 0)))
        return reserved

    def _batch_action(self,action):
        legacy=super()._batch_action(action)
        p=parse_action(legacy)
        if not self.enabled('resource_goal_guard') or p.verb!='craft':return legacy
        t=self.table; goal=parse_action(self.target).target; r=t.recipes.get(p.target,{})
        if goal in r.get('ingredients',[]) and (t.count(goal) or 0)<=self.amount:
            self.stage7_decision['D_protect_goal']={'rejected_craft':legacy,
                'reason':'public recipe consumes an owned final-goal copy still required by possession objective',
                'owned_lower_bound':t.count(goal),'required':self.amount}
            return 'wait'
        need=self.public_demand(p.target)
        deficit=max(1,math.ceil(need-(t.count(p.target) or 0))); reserves=self.reservations(p.target)
        conflicts=sorted(set(r.get('ingredients',[]))&set(reserves))
        counts=carried_counts(self.quantity_facts.table)
        samples=[x for x in self.quantity_facts.effects if x['target']==p.target and x['before_counts']==counts
                 and x.get('location')==t.state.get('location') and x['actual']>=deficit
                 and all(counts.get(k,0)-x['consumed'].get(k,0)>=v for k,v in reserves.items())] if counts is not None else []
        if samples:
            sample=min(samples,key=lambda x:(sum(x['consumed'].values()),x['requested']))
            amount=min(4,sample['requested']);reason='scoped_observed_effect_preserves_public_reserves'
        elif deficit>1 and self.public_quantity_rules.get(p.target) and all(
            (t.count(k) or 0)-math.ceil(v*min(4,deficit))>=reserves.get(k,0)
            for k,v in self.public_quantity_rules[p.target]['quantities'].items()):
            amount=min(4,deficit);reason='explicit_public_recipe_demand_and_reserve_margin'
        elif conflicts:
            amount=1;reason='unknown_or_insufficient_reserve_margin_use_minimum_trial'
        elif deficit>1:
            amount=min(4,deficit);reason='explicit_public_deficit_no_known_shared_material_conflict'
        else:
            amount=1;reason='unknown_quantity_no_public_demand_for_extra_copy'
        self.stage7_decision['D_batch']={'target':p.target,'legacy':legacy,'selected':amount,
            'deficit':deficit,'reserves_lower_bounds':reserves,'shared_inputs':conflicts,'reason':reason,
            'quantity_truth':'explicit public nominal weights when present; actual consumption and rounding UNKNOWN otherwise',
            'public_quantity_source':self.public_quantity_rules.get(p.target),
            'irreversible_trial_risk':not bool(samples),'matching_samples':len(samples)}
        self.mechanism_decision['batch'].update(requested=amount,rule=reason,
            predicted_consumption=samples[0]['consumed'] if len(samples)==1 else None)
        return f'craft {amount} {q(p.target)}'

    def choose(self,obs,base_action):
        self.stage7_decision={};self.last_ready=[]
        # C0 follows precisely the original call path and prompt. Added state is
        # audit-only and never changes the resource table or action selection.
        if not any(self.flags.values()):return super().choose(obs,base_action)
        if self.enabled('resource_goal_guard'):
            # Use a temporary table to avoid adding an extra observe to normal flow.
            original=self.table;self.table=copy.deepcopy(original);self.table.observe(obs)
            goal_action,reason=self._goal_action(base_action);self.table=original
            if goal_action:
                self.table.observe(obs);self.mechanism_decision={}
                self.stage7_decision['D_goal']={'reason':reason,'base_preserved':goal_action==base_action,'action':goal_action}
                self.last_choice={'node':parse_action(self.target).target,'action':goal_action,'structured_action':goal_action,
                    'queue':list(self.queue),'resource_table':self.table.to_dict(),'target':self.target,'reason':reason,'mechanisms':{}}
                action=goal_action
            else:action=super().choose(obs,base_action)
        else:action=super().choose(obs,base_action)
        if self.enabled('retry_context_fix') and not self.retry_allowed(action):
            rejected=action
            action=base_action if base_action!=action and self.retry_allowed(base_action) else 'wait'
            self.stage7_decision.setdefault('A_suppressed',[]).append({'action':rejected,'reason':'relevant failed condition unchanged','fallback':action})
        if self.enabled('explore_execute_switch'):self._set_mode(action)
        self.last_choice['action']=action;self.last_choice['stage7']=copy.deepcopy(self.stage7_decision)
        return action

    def observe(self,before,action,after):
        old_recipes={x for x,r in self.table.recipes.items() if r.get('ingredients')}
        p=parse_action(action); context=self.public_context(p.target); pending=copy.deepcopy(self.pending_probe)
        super().observe(before,action,after)
        if self.enabled('resource_goal_guard'):
            # Acquisition feedback contains explicit numerical recipe descriptions.
            # Use only already-known name lists; D does not discover extra recipes
            # or change the shared FIFO table / model fact summary.
            for name,body in re.findall(r'([\w-]+) \(([^)]+)\)',after.get('text','')):
                parts=[re.fullmatch(r'([\d.]+) ([\w-]+)',x.strip()) for x in body.split(',')]
                if parts and all(parts):
                    quantities={m[2]:float(m[1]) for m in parts}
                    if set(quantities)==set(self.table.recipes.get(name,{}).get('ingredients',[])):
                        self.public_quantity_rules[name]={'quantities':quantities,'step':after.get('step'),
                            'source':'explicit numerical recipe in public acquisition observation',
                            'evidence':name+' ('+body+')','scope':'nominal recipe quantities, engine rounding not inferred'}
        feedback=self.table.state['feedback'];new={x for x,r in self.table.recipes.items() if r.get('ingredients')}-old_recipes
        if self.enabled('retry_context_fix') and p.verb in {'craft','inspect'} and self.in_episode:
            success='successfully crafted' in feedback or 'I inspected ' in feedback
            failure='station' if 'Missing necessary' in feedback else 'materials' if 'Cannot craft a single' in feedback else 'not_accessible' if ('not see' in feedback or 'not found' in feedback or 'Cannot inspect' in feedback) else 'other'
            # Station names are first disclosed by this failure; its old availability
            # was false even when the pre-action table did not yet name the station.
            if failure=='station':context['stations']={s:False for s in self.table.recipes.get(p.target,{}).get('stations',[])}
            forward=bool(pending and pending['action'].startswith('craft ') and parse_action(pending['action']).target==p.target)
            record={'action':action,'target':p.target,'context':context,'feedback':feedback,
                'state':'SUCCESS' if success else 'BLOCKED_BY_PRECONDITION' if failure in {'station','materials','not_accessible'} else 'TESTED_WITH_RELEVANT_CONDITIONS',
                'meaningful_trial':success or failure=='other','failure_type':None if success else failure,
                'retry_condition':None if success else 'observed missing station present' if failure=='station' else 'observed relevant material increase' if failure=='materials' else 'observed accessibility change',
                'actual_action_cost':1,'observed_resource_consumption':None,
                'resource_status':'UNKNOWN until independently audited; failed attempt cost retained',
                'was_forward_trial':forward,'step':after.get('step')}
            prior=self.retry_records.get(p.verb+':'+p.target)
            record['retry_after_block']=bool(prior and prior['state']=='BLOCKED_BY_PRECONDITION' and success)
            self.retry_records[p.verb+':'+p.target]=record;self.attempt_log.append(record)
            self.events.append({'event':'stage7_attempt_result',**copy.deepcopy(record)})
            if forward and record['state']=='BLOCKED_BY_PRECONDITION':self.trials[p.target]=0
        if self.enabled('knowledge_gap_exploration'):
            relevant=self.update_gap()
            if pending:
                self.events.append({'event':'stage7_gap_result',**pending,'executed_action':action,
                    'new_recipes':sorted(new),'new_with_known_goal_connection':sorted(new&relevant),
                    'actual_action_cost':1,'observed_resource_consumption':None,
                    'value_status':'immediate_new_recipe' if new else 'delayed_or_unknown', 'feedback':feedback})
        if self.enabled('explore_execute_switch'):
            if p.verb=='craft' and 'Cannot ' in feedback:
                self.blocked_execution={'node':p.target,'feedback':feedback,'context':self.public_context(p.target),
                    'failure_type':'station' if 'Missing necessary' in feedback else 'materials' if 'Cannot craft a single' in feedback else 'unknown'}
                self.subgoals.setdefault(p.target,{})['blocked']=feedback
            if 'successfully crafted' in feedback or new:
                self.subgoals.setdefault(p.target,{}).update(last_progress_step=after.get('step'),blocked=None,
                    progress='production' if 'successfully crafted' in feedback else 'new_recipe')
            if self.blocked_execution:
                b=self.blocked_execution
                now=self.public_context(b['node']);old=b['context']
                released=(b['failure_type']=='station' and bool(now['stations']) and all(now['stations'].values())) or (
                    b['failure_type']=='materials' and any(v is not None and (old['materials'].get(k) is None or v>old['materials'][k]) for k,v in now['materials'].items()))
                if released or b['node'] in new or ('successfully crafted' in feedback and p.target==b['node']):
                    self.blocked_execution=None
        self.pending_probe=None

    @classmethod
    def from_dict(cls,data):
        obj=cls(**data.get('flags',{}));obj.__dict__.update(copy.deepcopy(data))
        obj.table=ResourceTable(**data['table']);obj.quantity_facts=PublicFacts.from_dict(data['quantity_facts'])
        return obj
