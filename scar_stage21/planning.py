"""One bounded public probe, never a multi-step task plan."""
import json
import re
from scar_stage20.planning import InterfaceError

KINDS = ('INSPECT_OBJECT', 'EXPLORE_FRONTIER', 'TEST_PUBLIC_HYPOTHESIS')
FIELDS = ('type', 'target', 'entry', 'evidence_ids', 'direction', 'uncertainty')
SYSTEM = '''Propose ONE short publicly executable exploration probe for the stated blocker.
The controller handles known crafting, quantities, workstations and the final task.
Do not output a full plan or material chain. Return exactly JSON fields:
{"type":"INSPECT_OBJECT|EXPLORE_FRONTIER|TEST_PUBLIC_HYPOTHESIS",
"target":"exact public name", "entry":"exact accessible public object or place",
"evidence_ids":["E..."],"direction":"brief hypothesis","uncertainty":["unknown relation"]}.
INSPECT_OBJECT checks one public object. EXPLORE_FRONTIER visits one public place.
TEST_PUBLIC_HYPOTHESIS checks the entry for information about the named blocker;
its causal relation may be UNKNOWN. Only cite IDs supplied in this prompt.
Do not invent objects, locations, recipes, quantities or future evidence.
A successful inspection or arrival is not material acquisition or task completion.'''


def validate(data):
    if not isinstance(data, dict) or set(data) != set(FIELDS) or data.get('type') not in KINDS:
        raise InterfaceError('schema_error', 'One public probe with exact fields is required')
    for key in ('target', 'entry', 'direction'):
        if not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 400:
            raise InterfaceError('schema_error', 'Invalid '+key)
    for key in ('evidence_ids', 'uncertainty'):
        if not isinstance(data[key], list) or len(data[key]) > 6 or any(not isinstance(x, str) or not x or len(x)>400 for x in data[key]):
            raise InterfaceError('schema_error', 'Invalid '+key)
    if not data['evidence_ids']: raise InterfaceError('schema_error', 'Evidence IDs are required')


def parse_response(raw):
    text = raw.strip(); events = []
    m = re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.S)
    if m: text=m[1].strip(); events.append('removed_single_code_fence')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise InterfaceError('schema_error', 'Duplicate JSON key')
            d[k]=v
        return d
    try: data=json.loads(text, object_pairs_hook=unique)
    except json.JSONDecodeError as exc: raise InterfaceError('invalid_JSON', str(exc)) from exc
    if isinstance(data, dict) and isinstance(data.get('uncertainty'), str):
        data['uncertainty']=[data['uncertainty']]; events.append('wrapped_uncertainty_string')
    validate(data)
    return data, events

