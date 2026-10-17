"""Public-prefix grounding and observation-driven execution of resource trials.

This first automatic adapter grounds one recipe at the CURRENT observed station.
The generic domain supports upstream recipes/routes; this adapter abstains when
that larger grounding is needed. Its goal is a method milestone, never a quest.
"""
from dataclasses import asdict
from fractions import Fraction
import re

from scar_public.causal_model import amounts, digest, outcome
from scar_public.resource_competition import (
    UNIT, Recipe, ResourceProblem, ResourceGap, compile_resources, select_experiment)


def milli(value):
    number = Fraction(str(value))*UNIT
    if number.denominator != 1 or number < 0:
        raise ResourceGap('quantity outside exact nonnegative milli-unit representation')
    return int(number)


def fresh(text):
    answer = {}
    for line in text.splitlines():
        if line.startswith('Current Location: '): answer['location'] = line[18:].strip()
        for prefix,suffix,key in [('I am holding ','.','holding'),('I have equipped ','.','equipped'),
                                  ('I see ',' near me.','ground')]:
            if line.startswith(prefix) and line.endswith(suffix):
                values = amounts(line[len(prefix):-len(suffix)])
                if values is None: raise ResourceGap('incomplete public '+key+' parse')
                answer[key] = values
    if any(k not in answer for k in ('location','holding','ground','equipped')):
        raise ResourceGap('missing fresh location or complete public inventory')
    return answer


def from_public(model, text, target):
    current = fresh(text); loc = current['location']
    recipe = model.recipes.get(target); station = model.stations.get(target)
    if not recipe or not station:
        raise ResourceGap('recipe quantity or target-specific station requirement not observed')
    if not current['ground'].get(station['name']):
        raise ResourceGap('station absent; automatic current-room grounding does not assert a route')
    if 'I was attacked' in text:
        raise ResourceGap('ambient combat is outside this resource model')
    # Container attachment is fixed in this adapter; never model a carried bag
    # as accessible after allowing that same bag to be dropped.
    equipped = [(n,b) for n,b in model.containers.items() if current['equipped'].get(n)]
    carried = [n for n in model.containers if current['holding'].get(n)]
    if len(equipped)>1 or carried:
        raise ResourceGap('requires exactly modeled attachment; held/multiple containers unsupported')
    name,bag = equipped[0] if equipped else (None,{'items':{},'used':0,'capacity':0})
    if bag.get('uncertain_after_craft'):
        raise ResourceGap('attached container contents stale; inspect before planning')
    needs = {n:milli(q) for n,q in recipe['needs'].items()}
    items = tuple(sorted(set(needs)|{target}|set(current['holding'])))
    contents = {n:milli(q) for n,q in bag['items'].items() if n in items}
    background = milli(bag['used'])-sum(contents.values())
    if background < 0: raise ResourceGap('unit-load abstraction conflicts with observed bag use')
    capacity = model.hand_capacity if model.hand_capacity is not None else model.capacity_lower
    if capacity <= 0: raise ResourceGap('no demonstrated hand capacity')
    assumptions = (
        'Candidate family coverage is unproved; observations may reject every model.',
        'One recipe/current observed room only; no claim of global task infeasibility.',
        'Goal is newly craft and hold this output; ingredients are not terminal requirements.',
        'Public recipe/station evidence may omit conditions; station presence is assumed sufficient.',
        'Unit load for modeled items, fixed equipment/capacity, fixed background bag load.',
        'Craft output is on the current floor; failure preserves materials; transfer moves one unit.',
        'Consumption priority is hand, attached bag, then current floor.',
        'No ambient item changes; attack feedback invalidates the resource-only execution certificate.',
        'Bag contents persist between inspected/explicit transfer events until uncertain crafting.',
        'Hand capacity is '+('an observed bound' if model.hand_capacity is not None else
                             'a conservative previously demonstrated bound, not an exact inferred limit')+'.',
    )
    return ResourceProblem(locations=(loc,),routes={},items=items,
        recipes=(Recipe(target,tuple(needs.items()),(loc,)),),start_location=loc,
        holding=current['holding'],ground={loc:{n:q for n,q in current['ground'].items() if n in items}},
        bag=contents,bag_name=name,hand_capacity=milli(capacity),bag_capacity=milli(bag['capacity']),
        hand_background=0,bag_background=background,target=target,assumptions=assumptions,
        source={'recipe':recipe['quote'],'station':station['quote'],'bag':bag.get('quote'),
                'public_prefix_length':len(model.history),'current_observation_sha256':digest(text),
                'equipment':current['equipped'],'hand_capacity_bounds':[model.capacity_lower,model.capacity_upper]})


def public_outcome(text, action):
    status = outcome(text,action)
    if status: return status
    for prefix,pattern,failed in (
        ('store ',r'I stored ([\d.]+) ([\w-]+) in ([\w-]+)\.', 'Cannot store '),
        ('take out ',r'I took out ([\d.]+) ([\w-]+) from ([\w-]+)\.', 'Cannot take out ')):
        if action.startswith(prefix):
            m = re.search(pattern,text)
            if m and action == prefix+' '.join(m.groups()): return 'success'
            if any(line.startswith(failed) for line in text.splitlines()): return 'failure'
    return None


class TrialSession:
    """Executes a certified contingent policy; actual feedback is never simulated.

    Frozen exemptions are NEVER recomputed after an experiment. Model mismatch,
    missing fields, changed equipment/background load, or combat invalidates the
    entire continuation. A discarded/exempt model is not a completed real task.
    """
    def __init__(self, compiled, result, witness, planner):
        if witness is None: raise ResourceGap('no verified witness to execute')
        self.compiled,self.result,self.planner = compiled,result,planner
        self.belief = compiled.belief
        self.prefix = list(witness.get('prefix',[])); self.suffixes = witness.get('suffixes')
        self.node = None if self.prefix else witness
        self.pending = None; self.events = []; self.status = 'ACTIVE'; self.used = 0
        self.crafted = set()

    def action(self):
        if self.status != 'ACTIVE': return None
        if self.pending: return self.pending
        if self.node and self.node.get('stop'):
            self.status = ('LOCAL_MILESTONE_CONFIRMED' if all(self.planner.goal.holds(s) for _,s in self.belief)
                           else 'REMAINING_MODELS_ORIGINALLY_INFEASIBLE')
            return None
        if self.used >= self.compiled.horizon:
            self.status = 'HORIZON_EXHAUSTED'; return None
        self.pending = self.prefix[0] if self.prefix else self.node['action']
        return self.pending

    def observe(self, text):
        if not self.pending: raise ValueError('no action awaiting public feedback')
        action = self.pending; self.pending = None; self.used += 1
        p = self.compiled.domain.problem; old_ids = {n for n,_ in self.belief}
        event = {'action':action,'observation_sha256':digest(text),'before_models':sorted(old_ids)}
        try:
            obs = fresh(text); status = public_outcome(text,action)
            if not status: raise ResourceGap('operation success/failure is not observed')
            if 'I was attacked' in text: raise ResourceGap('ambient combat outside resource model')
            if p.source and obs['equipped'] != p.source.get('equipment'):
                raise ResourceGap('equipment changed outside modeled action effects')
            if set(obs['holding'])-set(p.items):
                raise ResourceGap('unexpected held item changes modeled capacity background')
            if action.startswith('craft ') and status == 'success': self.crafted.add(action.split()[-1])
            vector = lambda values: tuple(values.get(n,0) for n in p.items)
            bag = None
            if action == 'inspect '+str(p.bag_name):
                content = re.search(r'It contains: (.*?) \(capacity: ([\d.]+)/([\d.]+)\)\.',text)
                if not content: raise ResourceGap('inspection does not expose complete container contents')
                values = amounts(content[1])
                if values is None: raise ResourceGap('container content parse incomplete')
                bag = vector(values)
                if milli(content[3]) != p.bag_capacity or milli(content[2])-sum(bag) != p.bag_background:
                    raise ResourceGap('container capacity/background load changed')
            observed = (status,obs['location'],vector(obs['holding']),vector(obs['ground']),
                        tuple(n in self.crafted for n in self.compiled.domain.recipe_order),bag)
            branches = self.planner.branches(self.belief,action)
            if observed not in branches:
                self.status = 'MODEL_MISMATCH'
                event.update(observed=observed,predictions=list(branches),surviving_models=[])
            else:
                self.belief = branches[observed]
                survivors = {n for n,_ in self.belief}
                event.update(observed=observed,surviving_models=sorted(survivors),
                             discriminated=survivors<old_ids)
                if self.prefix:
                    self.prefix.pop(0)
                    if not self.prefix: self.node = self.suffixes[observed]
                else: self.node = self.node['branches'][observed]
        except ResourceGap as error:
            self.status = 'OBSERVATION_GAP'; event['reason'] = str(error)
        event['status'] = self.status; self.events.append(event)
        return event

    def summary(self):
        self.action()  # Resolve an observed stop into a precisely named status.
        return {'status':self.status,'actions_used':self.used,'events':self.events,
                'surviving_models':sorted({n for n,_ in self.belief}),
                'full_task_completion_claimed':False,'fingerprint':self.compiled.fingerprint}


def make_trial(model, text, target, horizon=6, mode='preserve_opportunity', max_states=12000,
               expansion_budget=600, prefix_depth=2, max_prefixes=40, max_extra_actions=0,
               allowed_profiles=None):
    p = from_public(model,text,target)
    compiled = compile_resources(p,horizon=horizon,max_states=max_states,allowed_profiles=allowed_profiles)
    report,witness,planner = select_experiment(compiled,mode=mode,expansion_budget=expansion_budget,
        prefix_depth=prefix_depth,max_prefixes=max_prefixes,max_extra_actions=max_extra_actions)
    report['grounding'] = asdict(p)
    return report, TrialSession(compiled,report,witness,planner) if witness else None
