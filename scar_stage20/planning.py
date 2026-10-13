"""Small JSON interface: syntax/schema only; public validity is checked separately."""
import json
import re

KINDS = ('ACQUIRE_MATERIAL','LOCATE_PRECONDITION','CRAFT_PRECONDITION','INSPECT_OBJECT','EXPLORE_FRONTIER')
FIELDS = ('type','target','entry','evidence_ids','direction','uncertainty')
COMPLETION = dict(ACQUIRE_MATERIAL='OWNED_DEMAND',LOCATE_PRECONDITION='EXECUTABLE_PUBLIC_PATH',
    CRAFT_PRECONDITION='CRAFTED_OR_OWNED',INSPECT_OBJECT='INSPECTED',EXPLORE_FRONTIER='ARRIVED')
SYSTEM = '''Propose ONE bounded subgoal to resolve the specific public execution blocker.
The deterministic controller executes known rules, quantities, routes and area
prerequisites. Preserve the FINAL TASK. You do not output actions or a whole plan.
Return exactly: {"type": "...", "target": "...", "entry": "...",
"evidence_ids": ["E..."], "direction": "...", "uncertainty": ["..."]}.
type is ACQUIRE_MATERIAL, LOCATE_PRECONDITION, CRAFT_PRECONDITION,
INSPECT_OBJECT, or EXPLORE_FRONTIER. Use exact PUBLIC object/location identifiers.
entry is a publicly accessible object or reachable location at which to start.
Reference evidence IDs supplied in this request; never copy/quote JSON evidence.
Evidence must support the target or entry. Explain a short connection to the
specific blocker. Unknown hypotheses are allowed only through public entries;
do not claim hidden recipes/quantities/locations or invent new objects.
Use ACQUIRE_MATERIAL for a needed public resource; CRAFT_PRECONDITION when its
recipe is public; LOCATE_PRECONDITION when a named requirement lacks a usable
path. Inspecting an entry or reaching a candidate place does NOT complete LOCATE:
the controller verifies an actual public path. Completion is computed by code;
do not output a completion field. Avoid previous rejected/failed entries.
uncertainty must explicitly preserve unknowns. No global ranking or multi-plan.'''


class InterfaceError(ValueError):
    def __init__(self, category, detail):
        self.category = category
        super().__init__(detail)


def validate(data):
    if not isinstance(data,dict) or set(data)!=set(FIELDS) or data.get('type') not in KINDS:
        raise InterfaceError('schema_error','Invalid fields or subgoal type')
    for key in ('target','entry','direction'):
        if not isinstance(data[key],str) or not data[key].strip() or len(data[key])>800:
            raise InterfaceError('schema_error','Invalid string '+key)
    for key in ('evidence_ids','uncertainty'):
        if not isinstance(data[key],list) or len(data[key])>8 or any(not isinstance(v,str) or not v.strip() or len(v)>800 for v in data[key]):
            raise InterfaceError('schema_error','Invalid list '+key)
    if not data['evidence_ids']:
        raise InterfaceError('schema_error','At least one evidence reference is required')


def parse_response(raw):
    """Only lossless, unambiguous normalization; never repairs JSON quoting."""
    text=raw.strip();events=[]
    match=re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```',text,re.S)
    if match:text=match[1].strip();events.append('removed_single_code_fence')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise InterfaceError('schema_error','Duplicate JSON key')
            result[key]=value
        return result
    try:data=json.loads(text,object_pairs_hook=unique)
    except json.JSONDecodeError as exc:raise InterfaceError('invalid_JSON',str(exc)) from exc
    if isinstance(data,dict):
        for old,new in (('subgoal_type','type'),('evidence','evidence_ids')):
            if old in data:
                if new in data:raise InterfaceError('schema_error','Conflicting field alias')
                data[new]=data.pop(old);events.append('alias_'+old+'_to_'+new)
        if 'completion' in data:
            data.pop('completion');events.append('ignored_redundant_completion')
        if isinstance(data.get('uncertainty'),str) and data['uncertainty'].strip():
            data['uncertainty']=[data['uncertainty']];events.append('wrapped_uncertainty_string')
    validate(data)
    return data,events
