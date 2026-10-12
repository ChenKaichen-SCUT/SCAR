"""S1 executor plus the frozen P3 finish decision, without Stage15 dispatch.

Only direct_finish, ready, finish and local_collect were extracted from P3.
All FIFO, feedback, retry, exploration and batch implementations remain S1.
"""
import copy
import math
import re
from scar_sequence.planner import q
from scar_stage10.controller import ResourceController
from scar_unknown17.facts import PublicFacts
from scar_v3.state import parse_action
from .config import BaselineConfig, SCHEMA_VERSION, EPISODE_ACTIONS, FINISH_WINDOW
from .knowledge import PublicTable

class BaselineController(ResourceController):
    def __init__(self, variant='S1_P1_P3'):
        cfg = BaselineConfig(variant)
        if not cfg.knowledge_enabled:
            raise ValueError('S1 uses the unmodified ResourceController; use make_controller')
        super().__init__()
        self.variant16 = variant
        self.table = PublicTable()
        self.step16 = 0
        self.risk16 = False
        self.health16 = None
        self.audit16 = {}

    def set_goal(self, action, public_goal, follow_public=False):
        super().set_goal(action, public_goal, follow_public)
        self.step16 = 0

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
        if self.risk16:return None,{'reason':'public_health_or_combat_risk'}
        t=self.table;goal=parse_action(self.target).target;r=t.recipes.get(goal,{})
        if not r.get('quantities'):return None,{'reason':'final_nominal_requirements_UNKNOWN'}
        deficit=self.amount-(t.count(goal) or 0)
        if deficit<=0:return None,None
        if self.ready(goal):
            a=self._batch_action('craft 1 '+q(goal));lower=1+math.ceil(deficit)
            if lower<=EPISODE_ACTIONS-self.step16:
                return a,{'reason':'final_craft_then_collect','remaining_lower_bound':lower,'station_completeness':r.get('station_completeness','UNKNOWN')}
        # Only a single missing immediate material, available locally or itself
        # craftable now. No READY list, recursive synthesis, or goal relevance sort.
        missing=[n for n,v in r['quantities'].items() if (t.count(n) or 0)<v]
        if len(missing)!=1 or not all((t.state.get('ground') or {}).get(n,0)>0 for n in r.get('stations',[])):return None,None
        n=missing[0];lower=3+math.ceil(deficit)
        if lower>min(FINISH_WINDOW,EPISODE_ACTIONS-self.step16):return None,None
        if (t.state.get('ground') or {}).get(n,0)>=r['quantities'][n]-(t.count(n) or 0):
            a=self.local_collect(n,math.ceil(r['quantities'][n]-(t.count(n) or 0)))
        elif self.ready(n):a=self._batch_action('craft 1 '+q(n));lower+=1
        else:return None,{'reason':'missing_material_or_recipe','material':n}
        if a and lower<=min(FINISH_WINDOW,EPISODE_ACTIONS-self.step16):
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

    def choose(self, obs, base_action):
        # Same live update order as Stage15. The removed shadow S1 ran on a
        # detached copy and supplied audit data only, never a policy input.
        action = super().choose(obs, base_action)
        p1_action = action
        checks = []
        direct, _ = self.direct_finish(base_action)
        selected = None
        if self.variant16 == 'S1_P1_P3':
            candidate, meta = self.finish(base_action)
            checks.append({'module': 'finish', 'candidate': candidate, 'conditions': meta})
            if candidate and self.admissible(candidate, True):
                action, selected = candidate, 'finish'
            if direct:
                action, selected = direct, 'finish'
        self.audit16 = {
            'base_proposal': base_action, 'P1_action': p1_action,
            'selected': action, 'checks': checks,
            'modules': ['finish'] if self.variant16 == 'S1_P1_P3' else [],
            'selected_module': selected, 'remaining_actions': EPISODE_ACTIONS-self.step16,
        }
        self.last_choice.update(action=action, stage16=copy.deepcopy(self.audit16))
        return action

    def observe(self, before, action, after):
        super().observe(before, action, after)
        feedback = self.table.state['feedback']
        hp = re.search(r'My health is at ([\d.]+)', after['text'])
        new_hp = float(hp[1]) if hp else None
        self.risk16 = bool(re.search(
            r'draining \d+ HP|lost \d+ HP|is attacking|blocked the way out', feedback, re.I))
        if new_hp is not None and self.health16 is not None and new_hp < self.health16:
            self.risk16 = True
        self.health16 = new_hp
        if self.in_episode:
            self.step16 += 1

    @classmethod
    def from_dict(cls, data):
        data = copy.deepcopy(data)
        validate_frozen_core(data)
        obj = cls(data['variant16'])
        obj.__dict__.update(data)
        obj.table = PublicTable(**data['table'])
        obj.quantity_facts = PublicFacts.from_dict(data['quantity_facts'])
        return obj


def validate_frozen_core(state):
    expected = ResourceController().to_dict()
    for key in ('directed', 'batch', 'flags', 'opportunistic', 'storage'):
        if state.get(key) != expected[key]:
            raise ValueError(f'checkpoint changes frozen S1 option: {key}')


def make_controller(variant='S1_P1_P3'):
    cfg = BaselineConfig(variant)
    return BaselineController(variant) if cfg.knowledge_enabled else ResourceController()


def dump_controller(controller):
    return {'schema_version': SCHEMA_VERSION,
            'variant': getattr(controller, 'variant16', 'S1'),
            'state': copy.deepcopy(controller.to_dict())}


def restore_controller(checkpoint, expected_variant=None):
    data = copy.deepcopy(checkpoint)
    if data.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('unsupported controller schema')
    variant = BaselineConfig(data['variant']).variant
    if expected_variant is not None and variant != expected_variant:
        raise ValueError('cannot change configuration on an existing knowledge state')
    state = data['state']
    validate_frozen_core(state)
    if variant == 'S1':
        if 'knowledge' in state['table'] or 'knowledge15' in state['table'] or 'variant16' in state:
            raise ValueError('S1 checkpoint contains repaired knowledge')
        return ResourceController.from_dict(state)
    if state.get('variant16') != variant:
        raise ValueError('checkpoint variant mismatch')
    return BaselineController.from_dict(state)
