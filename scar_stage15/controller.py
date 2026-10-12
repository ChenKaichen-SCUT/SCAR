"""Small independent execution repairs over S1. Public observations only.

No environment, evaluator, task catalogue, hidden recipe, or additional model call.
Ordering: direct finish > near finish > bounded continuation > protect > quantity.
Quantity never extrapolates linear batch consumption and never globally shrinks.
"""
import copy
import math
import re
from collections import defaultdict
from scar_sequence.planner import q
from scar_stage10.controller import ResourceController
from scar_unknown17.facts import PublicFacts, carried_counts
from scar_v3.state import parse_action
from scar_stage15.knowledge import PublicTable

METHODS=['P0','P1','P2','P3','P4','P5','P6']
SWITCHES={'P1':(), 'P2':('quantity',), 'P3':('finish',), 'P4':('protect',), 'P5':('continue',),
          'P6':('quantity','finish','protect','continue')}


class Controller15(ResourceController):
    def __init__(self,method='P1'):
        super().__init__();self.method15=method;self.modules15=list(SWITCHES[method]);self.table=PublicTable()
        self.step15=0;self.audit15={};self.intent15=None;self.continuation15=None
        self.continuation_used15=0;self.continuation_selected15=False;self.protected15={}
        self.risk15=False;self.health15=None;self.loss15={};self.history15=[]

    def set_goal(self,action,public_goal,follow_public=False):
        super().set_goal(action,public_goal,follow_public);self.step15=0;self.intent15=None
        self.continuation15=None;self.continuation_used15=0

    def demand(self):
        """Sum one nominal operation per unmet public parent; not batch stoichiometry."""
        goal=parse_action(self.target).target;totals=defaultdict(float);sources=defaultdict(list)
        totals[goal]=self.amount
        nodes=self._all_needed(goal)
        for parent in sorted(nodes):
            threshold=self.amount if parent==goal else self.queue_needs.get(parent,1)
            if (self.table.count(parent) or 0)>=threshold:continue
            r=self.table.recipes.get(parent,{})
            for dep,value in (r.get('quantities') or {}).items():
                if dep in nodes:
                    totals[dep]+=value;sources[dep].append({'parent':parent,'nominal_per_operation':value})
        return dict(totals),dict(sources)

    def quantity(self,action):
        p=parse_action(action)
        if p.verb!='craft':return action,None
        t=self.table;recipe=t.recipes.get(p.target,{});nominal=recipe.get('quantities')
        demand,sources=self.demand();need=max(demand.get(p.target,0),self.amount if p.target==parse_action(self.target).target else self.queue_needs.get(p.target,1))
        deficit=max(0,math.ceil(need-(t.count(p.target) or 0)))
        meta={'original':action,'target':p.target,'nominal':nominal,'batch_expected_consumption':'UNKNOWN',
              'deficit':deficit,'public_parent_demands':sources.get(p.target,[]),'reason':'retain_S1_unknown_batch_semantics'}
        if nominal:
            missing=[n for n,v in nominal.items() if self.ownership(n)['exact'] and (t.count(n) or 0)<v]
            meta['known_insufficient_for_one_operation']=missing
            for n in missing:
                candidate=self._acquire(n,max(nominal[n],demand.get(n,0)),set(nominal))
                if candidate and self.admissible(candidate,True):
                    return candidate,meta | {'reason':'acquire_explicit_nominal_shortfall','missing':n}
        # A scoped, observed sample may select a batch only at identical public
        # starting inventory and location. Environment-contaminated deltas remain
        # samples, never recipes; no unobserved craft1-vs-craft2 superiority claim.
        counts=carried_counts(t)
        samples=[s for s in self.quantity_facts.effects if s['target']==p.target and s['before_counts']==counts
                 and s.get('location')==t.state.get('location') and s['actual']>=max(1,deficit)
                 and s['requested']>=int(p.args[0]) and 1<=s['requested']<=4] if counts is not None else []
        if samples:
            sample=min(samples,key=lambda s:(sum(s['consumed'].values()),s['requested']))
            meta.update(reason='identical_public_context_observed_sample',sample=sample)
            return f"craft {sample['requested']} {q(p.target)}",meta
        if deficit>int(p.args[0]) and nominal and len(sources.get(p.target,[]))>1:
            return f'craft {min(4,deficit)} {q(p.target)}',meta | {'reason':'shared_public_parent_demand_raise_request_only','actual_output':'UNKNOWN'}
        return action,meta

    def direct_finish(self,base):
        t=self.table;goal=parse_action(self.target).target;own=t.count(goal) or 0
        if own>=self.amount:return None,None
        hands=t.state.get('hands');ground=t.state.get('ground') or {};left=self.amount-own
        if hands is not None and sum(hands.values())<2:
            if ground.get(goal,0)>0:
                a='pick up '+q(goal)
                return a,{'reason':'visible_final_product','remaining_lower_bound':math.ceil(left),'direct':left<=1}
            for name,c in sorted(t.containers.items()):
                if not t.carried(name) and t.access(name) and (c.get('counts') or {}).get(goal,0)>0:
                    return f'take out {q(goal)} {q(name)}',{'reason':'accessible_final_product','remaining_lower_bound':math.ceil(left),'direct':left<=1}
        return None,None

    def ready(self,item):
        t=self.table;r=t.recipes.get(item,{});quantities=r.get('quantities')
        return bool(quantities and all((t.count(n) or 0)>=v for n,v in quantities.items())
                    and all((t.state.get('ground') or {}).get(n,0)>0 for n in r.get('stations',[]))
                    and self.retry_allowed('craft 1 '+q(item)))

    def finish(self,base):
        action,meta=self.direct_finish(base)
        if action:return action,meta
        if self.risk15:return None,{'reason':'public_health_or_combat_risk'}
        t=self.table;goal=parse_action(self.target).target;r=t.recipes.get(goal,{})
        if not r.get('quantities'):return None,{'reason':'final_nominal_requirements_UNKNOWN'}
        deficit=self.amount-(t.count(goal) or 0)
        if deficit<=0:return None,None
        if self.ready(goal):
            a=self._batch_action('craft 1 '+q(goal));lower=1+math.ceil(deficit)
            if lower<=40-self.step15:
                return a,{'reason':'final_craft_then_collect','remaining_lower_bound':lower,'station_completeness':r.get('station_completeness','UNKNOWN')}
        # Only a single missing immediate material, available locally or itself
        # craftable now. No READY list, recursive synthesis, or goal relevance sort.
        missing=[n for n,v in r['quantities'].items() if (t.count(n) or 0)<v]
        if len(missing)!=1 or not all((t.state.get('ground') or {}).get(n,0)>0 for n in r.get('stations',[])):return None,None
        n=missing[0];lower=3+math.ceil(deficit)
        if lower>min(6,40-self.step15):return None,None
        if (t.state.get('ground') or {}).get(n,0)>=r['quantities'][n]-(t.count(n) or 0):
            a=self.local_collect(n,math.ceil(r['quantities'][n]-(t.count(n) or 0)))
        elif self.ready(n):a=self._batch_action('craft 1 '+q(n));lower+=1
        else:return None,{'reason':'missing_material_or_recipe','material':n}
        if a and lower<=min(6,40-self.step15):
            return a,{'reason':'single_local_final_dependency','material':n,'remaining_lower_bound':lower}
        return None,None

    def local_collect(self,item,amount=1):
        t=self.table;s=t.state;hands=s.get('hands');ground=s.get('ground') or {}
        if not ground.get(item,0):return None
        if hands is not None and sum(hands.values())<2 and amount==1:return 'pick up '+q(item)
        if t.inventory:
            c=t.containers.get(t.inventory,{});load=c.get('load');cap=c.get('capacity')
            # Unknown volume/capacity is not a certified safe protection transfer.
            if load is not None and cap is not None and cap>load:
                count=int((hands or {}).get(item,0)+min(ground[item],amount))
                a=f'store {count} {q(item)} inventory'
                if self.admissible(a,True):return a
        return None

    def protect(self,action):
        t=self.table;s=t.state;goal=parse_action(self.target).target
        if self.risk15 or (self.health15 is not None and self.health15<=30):return None,{'reason':'known_carry_health_risk'}
        if self.step15>=38:return None,{'reason':'insufficient_finish_reserve'}
        if self.direct_finish(action)[0]:return None,{'reason':'direct_finish_has_priority'}
        departing=parse_action(action).verb=='enter'
        if not departing and not self.loss15.get(s.get('location')):return None,None
        demand,_=self.demand();nodes=self._all_needed(goal)-{goal}
        for item in sorted(nodes):
            key=str(s.get('location'))+':'+item
            if key in self.protected15:continue
            # Unknown quantities support only one presence-protection trial;
            # they never become numerical recipe knowledge.
            need=demand.get(item);owned=t.count(item) or 0
            if owned>=(need if need is not None else 1):continue
            amount=max(1,math.ceil((need or 1)-owned))
            candidate=self.local_collect(item,amount)
            if candidate and self.admissible(candidate,True):
                return candidate,{'reason':'protect_public_dependency_before_departure' if departing else 'previous_public_local_loss',
                    'item':item,'needed_quantity':need if need is not None else 'UNKNOWN','ground':s['ground'].get(item),
                    'extra_action':1,'key':key,'capacity_note':'nonfull observed container; item volume UNKNOWN'}
        return None,None

    def continuation_next(self):
        intent=self.intent15;t=self.table
        if not intent or intent.get('actual_actions',0)<1 or self.exploration_spent<18 or self.continuation_used15>=7:return None,None
        if self.risk15 or self.step15>=40 or self.direct_finish('wait')[0]:return None,{'stop':'risk_budget_or_direct_finish'}
        product=intent['product'];r=t.recipes.get(product,{})
        if intent.get('stopped'):return None,{'stop':intent['stopped']}
        if intent.get('produced'):
            if product not in t.inspected and product in self.visible():return 'inspect '+q(product),{'reason':'inspect_already_produced_accepted_trial','product':product}
            return None,{'stop':'complete_or_product_inaccessible'}
        if not r.get('ingredients'):return None,{'stop':'recipe_relation_lost'}
        for dep in r['ingredients']:
            need=(r.get('quantities') or {}).get(dep,1)
            if (t.count(dep) or 0)<need:
                a=self._acquire(dep,need,set(r['ingredients']))
                if a and parse_action(a).verb in {'enter','store','pick up','take out','inspect','equip'} and self.admissible(a,True):
                    return a,{'reason':'finish_accepted_trial_preparation','product':product,'nominal_quantity':(r.get('quantities') or {}).get(dep,'UNKNOWN')}
                return None,{'stop':'physical_material_unavailable'}
        stations=r.get('stations')
        if stations and not all((t.state.get('ground') or {}).get(n,0)>0 for n in stations):
            # No new exploration: use only an already observed station location.
            for loc,data in t.places.items():
                if all(n in data['objects'] for n in stations):
                    a=self._move(loc)
                    if a and self.admissible(a,True):return a,{'reason':'accepted_trial_known_station','product':product}
            return None,{'stop':'physical_station_unavailable'}
        a=self._batch_action('craft 1 '+q(product))
        if self.retry_allowed(a) and self.admissible(a,True):return a,{'reason':'complete_accepted_trial_craft','product':product,'unknown_station_trial':stations is None}
        return None,{'stop':'physical_precondition_block'}

    def choose(self,obs,base_action):
        # Shadow S1 receives precisely the same saved public state and proposal;
        # its parser stays frozen. The shadow makes no API or native calls.
        old=ResourceController.from_dict(self.legacy_state())
        old_action=old.choose(obs,base_action)
        action=super().choose(obs,base_action);p1=action;checks=[]
        self.continuation_selected15=False
        direct,dmeta=self.direct_finish(base_action)
        selected=None
        if 'finish' in self.modules15:
            candidate,meta=self.finish(base_action);checks.append({'module':'finish','candidate':candidate,'conditions':meta})
            if candidate and self.admissible(candidate,True):action=candidate;selected='finish'
        if 'continue' in self.modules15 and selected is None:
            candidate,meta=self.continuation_next();checks.append({'module':'continue','candidate':candidate,'conditions':meta})
            if candidate:
                action=candidate;selected='continue';self.continuation_selected15=True
                if self.continuation15 is None:self.continuation15={'product':self.intent15['product'],'start':self.step15}
            elif meta and meta.get('stop') and self.intent15:self.intent15['stopped']=meta['stop']
        if 'protect' in self.modules15 and selected is None:
            candidate,meta=self.protect(action);checks.append({'module':'protect','candidate':candidate,'conditions':meta})
            if candidate:
                action=candidate;selected='protect';self.protected15[meta['key']]=self.step15
        if 'quantity' in self.modules15 and not (selected=='finish' and direct):
            action,meta=self.quantity(action)
            if meta:checks.append({'module':'quantity','candidate':action,'conditions':meta})
        # Preserve a genuinely immediate final acquisition even in the combined
        # method. Other modules may not consume that action's final-step budget.
        if direct and ('finish' in self.modules15):action=direct;selected='finish';self.continuation_selected15=False
        self.audit15={'base_proposal':base_action,'shadow_S1_action':old_action,'P1_action':p1,'selected':action,
                      'checks':checks,'modules':self.modules15,'selected_module':selected,'remaining_actions':40-self.step15,
                      'intent':copy.deepcopy(self.intent15),'continuation_used':self.continuation_used15}
        self.last_choice.update(action=action,stage15=copy.deepcopy(self.audit15))
        return action

    def legacy_state(self):
        data=self.to_dict();data['table'].pop('knowledge15',None)
        # This shadow is a same-current-public-state action comparison, not a
        # claim that frozen S1 would have reached this different history.
        return {k:v for k,v in data.items() if not k.endswith('15')}

    def observe(self,before,action,after):
        pending=copy.deepcopy(self.pending_probe);before_ground=copy.deepcopy(self.table.state.get('ground') or {})
        before_loc=self.table.state.get('location');old_facts=len(self.table.knowledge15.events)
        super().observe(before,action,after);feedback=self.table.state['feedback'];p=parse_action(action)
        hp=re.search(r'My health is at ([\d.]+)',after['text']);new_hp=float(hp[1]) if hp else None
        # Native public health feedback only; no hidden curse item catalogue.
        self.risk15=bool(re.search(r'draining \d+ HP|lost \d+ HP|is attacking|blocked the way out',feedback,re.I))
        if new_hp is not None and self.health15 is not None and new_hp<self.health15:self.risk15=True
        self.health15=new_hp
        if before_loc==self.table.state.get('location') and p.verb not in {'store','pick up','craft','discard','drop','take out'}:
            lost={n:v-(self.table.state.get('ground') or {}).get(n,0) for n,v in before_ground.items() if v>(self.table.state.get('ground') or {}).get(n,0)}
            if lost:self.loss15[before_loc]=lost
        rejected=bool(re.search(r'Cannot |Invalid ',feedback))
        matched=bool(pending and (parse_action(pending['action']).verb,parse_action(pending['action']).target)==(p.verb,p.target))
        if matched and not rejected and not self.continuation_selected15:
            source=pending.get('source',{});product=source.get('product') or source.get('recipe')
            if product:
                if not self.intent15 or self.intent15['product']!=product:
                    self.intent15={'product':product,'accepted_action':action,'accepted_step':after['step'],'actual_actions':0,'produced':False}
                self.intent15['actual_actions']+=1
        if self.intent15:
            deps=self.table.recipes.get(self.intent15['product'],{}).get('ingredients',[])
            related=p.target in [self.intent15['product'],*deps] and p.verb in {'craft','inspect','store','pick up','take out'}
            if not self.continuation_selected15 and not matched and not related:
                self.intent15['stopped']='intervening_unrelated_action_intent_no_longer_active'
            if self.continuation_selected15:
                self.continuation_used15+=1
                if rejected:self.intent15['stopped']='first_failed_continuation_action'
                if self.risk15:self.intent15['stopped']='new_public_health_or_combat_risk'
                if self.continuation_used15>=7:self.intent15['stopped']='seven_actual_action_limit'
            if p.verb=='craft' and p.target==self.intent15['product'] and 'successfully crafted' in feedback:self.intent15['produced']=True
            if p.verb=='inspect' and p.target==self.intent15['product'] and 'I inspected ' in feedback:self.intent15['stopped']='production_and_inspection_complete'
            # New goal recipe information can invalidate an old speculative plan.
            goal=parse_action(self.target).target
            changes=self.table.knowledge15.events[old_facts:]
            if any(e['product']==goal and 'new_relation' in e['changes'] for e in changes):self.intent15['stopped']='new_final_recipe_information'
        if self.in_episode:
            self.history15.append({'step':self.step15,'action':action,'feedback':feedback,'audit':copy.deepcopy(self.audit15),
                                   'continuation_selected':self.continuation_selected15,'intent_after':copy.deepcopy(self.intent15)})
            self.history15=self.history15[-1:];self.step15+=1
        self.continuation_selected15=False

    @classmethod
    def from_dict(cls,data):
        data=copy.deepcopy(data)
        obj=cls(data.get('method15','P1'));obj.__dict__.update(copy.deepcopy(data))
        obj.table=PublicTable(**data['table']);obj.quantity_facts=PublicFacts.from_dict(data['quantity_facts']);return obj
