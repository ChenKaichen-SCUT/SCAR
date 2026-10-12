"""Explicit historical checkpoint import, separate from the production factory.

This does not enable configuration switching on an enriched live state. Only
original S1/P0, P1 and P3 states with their own histories are accepted.
"""
import copy
from .controller import make_controller, dump_controller, restore_controller

AUDIT_FIELDS = ('base_proposal', 'P1_action', 'selected', 'checks', 'modules',
                'selected_module', 'remaining_actions')


def migrate_state(data, variant):
    data = copy.deepcopy(data)
    if variant == 'S1':
        if any(k.endswith('15') or k.endswith('16') for k in data) or 'knowledge15' in data['table']:
            raise ValueError('S1 must use its own original checkpoint')
    else:
        expected = {'S1_P1': 'P1', 'S1_P1_P3': 'P3'}.get(variant)
        if expected is None or data.get('method15') != expected:
            raise ValueError('historical method does not match selected variant')
        data['table']['knowledge'] = data['table'].pop('knowledge15')
        audit = data.get('audit15') or {}
        fields = {'variant16': variant, 'step16': data['step15'],
                  'risk16': data['risk15'], 'health16': data['health15'],
                  'audit16': {k: audit[k] for k in AUDIT_FIELDS if k in audit}}
        data = {k: v for k, v in data.items() if not k.endswith('15')}
        data.update(fields)
        last = data.get('last_choice') or {}
        if 'knowledge15' in last.get('resource_table', {}):
            last['resource_table']['knowledge'] = last['resource_table'].pop('knowledge15')
        if 'stage15' in last:
            audit = last.pop('stage15')
            last['stage16'] = {k: audit[k] for k in AUDIT_FIELDS if k in audit}
    envelope = dump_controller(make_controller(variant))
    envelope['state'] = data
    return restore_controller(envelope, variant)


def migrate_facts(data, variant):
    from scar_unknown17.facts import PublicFacts
    from .knowledge import PublicFacts16
    data = copy.deepcopy(data)
    if variant == 'S1':
        if 'knowledge15' in data['table'] or 'knowledge' in data['table']:
            raise ValueError('cannot disable P1 on an enriched fact state')
        return PublicFacts.from_dict(data)
    data['table']['knowledge'] = data['table'].pop('knowledge15')
    return PublicFacts16.from_dict(data)
