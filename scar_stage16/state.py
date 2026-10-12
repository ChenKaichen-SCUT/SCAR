"""Read-only public-state snapshots. No engine, ranking or speculative rules.

Create a fresh snapshot after observe_transition. Query results are detached
copies; neither callers nor queries can mutate the live controller. S1 exposes
its legacy records explicitly and never runs the P1 parser through this view.
"""
import copy
from scar_sequence.planner import q
from scar_v3.state import parse_action
from .controller import dump_controller, restore_controller

KNOWN, UNKNOWN, CONFLICTED = 'KNOWN', 'UNKNOWN', 'CONFLICTED'


def field(value, conflict=False):
    return {'status': CONFLICTED if conflict else UNKNOWN if value is None else KNOWN,
            'value': copy.deepcopy(value)}


class PublicRuleState:
    def __init__(self, controller):
        self._controller = restore_controller(dump_controller(controller))
        self._table = self._controller.table

    def get_recipe(self, item):
        t = self._table
        knowledge = getattr(t, 'knowledge', None)
        f = (knowledge.facts.get(item) or {}) if knowledge else t.recipes.get(item, {})
        conflict = f.get('certainty') == 'AMBIGUOUS_CONFLICT'
        # S1 observed consumption averages are not nominal public recipe weights.
        quantities = f.get('quantities') if knowledge else None
        relation = f.get('ingredients') or None
        stations = f.get('stations') or None
        fields = {'materials': field(relation, conflict), 'quantities': field(quantities, conflict),
                  'stations': field(stations, conflict)}
        missing = [name for name, data in fields.items() if data['status'] != KNOWN]
        # The parser can disclose only a subset of necessary stations. It never
        # certifies an empty or exhaustive station list, nor batch consumption.
        missing += ['station_completeness', 'batch_consumption']
        return {'product': item, 'status': CONFLICTED if conflict else KNOWN if f else UNKNOWN,
                **fields, 'first_relation_step': f.get('first_relation_step'),
                'first_quantity_step': f.get('first_quantity_step'),
                'first_observed_step': f.get('observed_step', f.get('step')),
                'source_action': f.get('source_action'), 'raw_evidence': f.get('raw_evidence'),
                'evidence_ids': list(f.get('evidence_ids', [])),
                'station_completeness': field(None), 'batch_consumption': field(None),
                'complete': False, 'missing_conditions': missing,
                'source_mode': 'P1_native_evidence' if knowledge else 'S1_legacy_record',
                'as_of_step': t.state.get('step')}

    def get_known_dependencies(self, item):
        recipe = self.get_recipe(item)
        material = recipe['materials']
        return {'product': item, 'status': material['status'],
                'dependencies': material['value'] if material['status'] == KNOWN else [],
                'evidence_ids': recipe['evidence_ids']}

    def get_missing_knowledge(self, goal=None):
        goal = goal or parse_action(self._controller.target).target
        pending, seen, gaps = [goal], set(), []
        while pending:
            item = pending.pop(0)
            if item in seen:
                continue
            seen.add(item)
            recipe = self.get_recipe(item)
            gaps.append({'product': item, 'status': recipe['status'],
                         'missing_conditions': recipe['missing_conditions']})
            pending.extend(self.get_known_dependencies(item)['dependencies'])
        return {'goal': goal, 'gaps': gaps,
                'scope': 'currently disclosed dependency graph only; leaf recipes can be UNKNOWN'}

    def get_available_materials(self):
        t = self._table
        current = {name: field(t.state.get(name)) for name in ('hands', 'equipment', 'ground')}
        names = dict.fromkeys(n for k in ('hands', 'equipment') for n in (t.state.get(k) or {}))
        containers = []
        for name, record in t.containers.items():
            if not t.access(name):
                continue
            carried = t.carried(name)
            if carried:
                names.update(dict.fromkeys(record.get('counts') or {}))
            containers.append({'container': name, 'carried': carried,
                               'last_observed_counts': field(record.get('counts')),
                               'observed_step': record.get('step'),
                               'current_contents_certainty': UNKNOWN,
                               'scope': 'historical public counts; unobserved external changes not excluded'})
        owned = {}
        for name in names:
            own = self._controller.ownership(name)
            owned[name] = {'lower_bound': own['lower_bound'], 'complete_public_accounting': own['exact'],
                           'status': KNOWN if own['exact'] else UNKNOWN,
                           'scope': 'public accounting, not hidden current-world verification'}
        return {'as_of_step': t.state.get('step'), 'current': current,
                'owned_public_accounting': owned, 'accessible_containers': containers}

    def get_rule_evidence(self, item):
        knowledge = getattr(self._table, 'knowledge', None)
        recipe = self.get_recipe(item)
        return {'product': item, 'status': recipe['status'],
                'first_relation_step': recipe['first_relation_step'],
                'first_quantity_step': recipe['first_quantity_step'],
                'events': copy.deepcopy([e for e in knowledge.events if e['product'] == item]) if knowledge else [],
                'provenance_available': knowledge is not None}

    def get_execution_status(self, item):
        c, t = self._controller, self._table
        action = 'craft 1 '+q(item)
        assessment = copy.deepcopy(c.assess(action))  # pure frozen S1 query
        recipe = self.get_recipe(item)
        nominal = []
        if recipe['quantities']['status'] == KNOWN:
            for material, required in recipe['quantities']['value'].items():
                own = c.ownership(material)
                status = 'SUPPORTED' if own['lower_bound'] >= required else 'REJECT' if own['exact'] else UNKNOWN
                nominal.append({'material': material, 'nominal_required': required,
                                'owned': own, 'status': status})
        return {'product': item, 's1_assessment': assessment, 'nominal_material_conditions': nominal,
                'blockers': [v for v in assessment['conditions'] if v['status'] == 'REJECT'] +
                            [v for v in nominal if v['status'] == 'REJECT'],
                'knowledge_status': recipe['status'], 'unknown_conditions': recipe['missing_conditions'],
                'retry_allowed': c.retry_allowed(action), 'as_of_step': t.state.get('step'),
                'scope': 'public conditions only; not a craft feasibility guarantee or P2 policy'}

    def get_goal_status(self):
        c, t = self._controller, self._table
        goal = parse_action(c.target).target
        own = c.ownership(goal)
        complete = own['lower_bound'] >= c.amount
        opportunities = []
        hands = t.state.get('hands')
        if not complete and hands is not None and sum(hands.values()) < 2:
            if (t.state.get('ground') or {}).get(goal, 0) > 0:
                opportunities.append('pick up '+q(goal))
            for name, rec in t.containers.items():
                if not t.carried(name) and t.access(name) and (rec.get('counts') or {}).get(goal, 0) > 0:
                    opportunities.append(f'take out {q(goal)} {q(name)}')
        return {'goal': goal, 'required': c.amount, 'owned': own, 'complete': complete,
                'completion_status': KNOWN if complete or own['exact'] else UNKNOWN,
                'completion_basis': 'owned public accounting; production or ground presence alone never sufficient',
                'direct_acquisition_actions': opportunities, 'execution': self.get_execution_status(goal)}

    def get_uninspected_objects(self):
        t = self._table
        objects = {}
        for place, record in t.places.items():
            for name in record.get('objects', {}):
                objects.setdefault(name, []).append({'location': place, 'observed_step': record.get('step'),
                                                     'scope': 'historical last-seen presence'})
        for container, record in t.containers.items():
            for name in record.get('counts') or {}:
                objects.setdefault(name, []).append({'location': record.get('location'),
                    'container': container, 'observed_step': record.get('step'),
                    'scope': 'historical last-observed container contents'})
        for kind in ('hands', 'equipment', 'ground'):
            for name in t.state.get(kind) or {}:
                objects.setdefault(name, []).append({'location': t.state.get('location'),
                    'observed_step': t.state.get('step'), 'scope': 'current '+kind})
        return [{'object': name, 'observations': copy.deepcopy(observations)}
                for name, observations in objects.items() if name not in t.inspected]
