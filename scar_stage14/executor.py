"""One bounded public executor, independent of algorithms and evaluation truth.

K2 planning is deliberately frozen to the historical public representation;
K1 is a separate measurement calibration. No hidden native objects are accepted.
"""
import re
from scar.io import digest
from scar_sequence.planner import q
from scar_stage12.public import controller, confirmed
from scar_stage10.controller import REJECT
from scar_v3.state import parse_action


class Executor:
    def __init__(self, public, intent):
        self.ctrl=controller(public['controller'],public['observation'])
        self.intent=intent;self.trace=[];self.used=set();self.stop=None
        self.completed=False;self.completion_step=None;self.made=False
        self.remaining=min(8,public['remaining_actions'])

    def _finish(self,reason,complete=False):
        self.stop=reason;self.completed=complete
        if complete:self.completion_step=len(self.trace)
        return None

    def next(self):
        if self.stop:return None
        if len(self.trace)>=self.remaining:return self._finish('action_budget')
        if not self.trace:action=self.intent['first_action']
        else:
            action=self._continuation()
            if action is None:return None
        signature=digest([action,self.ctrl.context(action)])
        if signature in self.used:return self._finish('same_context_repeat')
        self.used.add(signature)
        return action

    def _continuation(self):
        t=self.ctrl.table;i=self.intent;name=i['target'];op=i['operation']
        if op=='atomic':return self._finish('atomic_intent_incomplete')
        if op in {'move','visit_inspect'}:
            if t.state.get('location')!=i['location']:
                a=self.ctrl._move(i['location'])
                return a if a else self._finish('public_route_unavailable')
            if op=='move':return self._finish('destination_reached_no_exploration_goal',True)
            if name not in self.ctrl.visible():return self._finish('target_no_longer_publicly_accessible')
            return 'inspect '+q(name)
        if op=='inspect':return self._finish('inspection_failed')
        if op!='craft_inspect':return self._finish('unsupported_intent')
        if self.made:
            if name in self.ctrl.visible():return 'inspect '+q(name)
            return self._finish('witnessed_product_no_longer_accessible')
        recipe=t.recipes.get(name,{})
        deps=recipe.get('ingredients',[])
        # No recursive synthesis and no hidden missing-ingredient completion.
        # A known station-only goal permits a bounded real trial at its station.
        for dep in deps:
            need=(recipe.get('quantities') or {}).get(dep,self.ctrl.quotas.get(name,1))
            if (t.count(dep) or 0)<need:
                a=self.ctrl._acquire(dep,need,confirmed(self.ctrl)|set(deps))
                return a if a else self._finish('public_material_unavailable')
        stations=recipe.get('stations',[])
        ground=t.state.get('ground') or {}
        if stations and not all(x in ground for x in stations):
            places=[loc for loc,data in sorted(t.places.items()) if all(x in data['objects'] for x in stations)]
            if not places:return self._finish('public_station_location_unknown')
            a=self.ctrl._move(places[0])
            return a if a else self._finish('public_station_route_unavailable')
        if not deps and not stations:return self._finish('recipe_and_conditions_unknown')
        action=self.ctrl._batch_action('craft 1 '+q(name))
        if self.ctrl.assess(action)['status']==REJECT:return self._finish('public_precondition_rejected')
        return action

    def observe(self,action,before,after):
        assert len(self.trace)<self.remaining
        self.ctrl.observe(before,action,after)
        feedback=self.ctrl.table.state['feedback'];p=parse_action(action)
        self.trace.append({'action':action,'before':before,'after':after,'feedback':feedback})
        # Explicit native feedback plus current accessibility, never a scoring field.
        if p.verb=='craft' and p.target==self.intent['target']:
            if re.search(r'\bI successfully crafted [\d.]+ '+re.escape(p.target)+r'\.',feedback):
                self.made=True
        op=self.intent['operation']
        if p.verb=='inspect' and p.target==self.intent['target'] and feedback.startswith('I inspected '+p.target+':'):
            if op in {'inspect','visit_inspect'} or (op=='craft_inspect' and self.made):
                self._finish('intent_complete',True)
        elif op=='atomic':
            if p.verb in {'store','pick up','take out'}:
                # Success of acquisition itself; downstream exploration remains incomplete.
                ok=feedback.startswith(('I stored ','I picked up ','I took out '))
                self._finish('atomic_acquisition_complete' if ok else 'atomic_action_failed',ok)
            else:self._finish('atomic_intent_incomplete')
        elif op=='move' and self.ctrl.table.state.get('location')==self.intent['location']:
            self._finish('destination_reached_no_exploration_goal',True)
        owned=self.ctrl.ownership(parse_action(self.ctrl.target).target)['lower_bound']
        amount=self.ctrl.amount
        if not self.stop and isinstance(owned,(float,int)) and isinstance(amount,(float,int)) and owned>=amount:
            self._finish('public_goal_satisfied')

    def result(self):
        return {'stop':self.stop or 'action_budget','intent_complete':self.completed,
                'completion_step':self.completion_step,'actions':len(self.trace),
                'exploration_intent_explicit':self.intent['clarity']=='explicit'}
