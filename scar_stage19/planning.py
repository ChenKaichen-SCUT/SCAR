"""Real JSON subgoal protocol. No fabricated action field or dummy model call."""
KINDS = ('ACQUIRE_MATERIAL', 'LOCATE_PRECONDITION', 'CRAFT_PRECONDITION',
         'INSPECT_OBJECT', 'EXPLORE_FRONTIER')
FIELDS = ('type', 'target', 'entry', 'public_evidence', 'direction', 'completion', 'uncertainty')
COMPLETION = dict(ACQUIRE_MATERIAL='OWNED', LOCATE_PRECONDITION='PUBLIC_PATH_OR_RECIPE',
                  CRAFT_PRECONDITION='CRAFTED_OR_OWNED', INSPECT_OBJECT='INSPECTED',
                  EXPLORE_FRONTIER='ARRIVED')
SYSTEM = '''You plan one bounded subgoal for a deterministic public-evidence game controller.
The controller has the final task and executes known dependencies without you.
You are called ONLY when it has no reliable next action or is blocked. Preserve
the final task. Never claim an unknown recipe, quantity, location or object type
is known. Missing necessary X proves a required object in the CURRENT AREA,
not its type, hidden recipe or acquisition method. Hypotheses are allowed but
must start at a publicly observed object or reachable frontier. Do not issue raw
actions, Python, a full plan, or fictitious facts. Consider recorded unsuccessful
intents and avoid repeats. A useful intermediate can be crafted and inspected to
discover links, but explain the uncertainty and its connection to the blocker.
Return one JSON object with exactly these fields:
type: ACQUIRE_MATERIAL | LOCATE_PRECONDITION | CRAFT_PRECONDITION | INSPECT_OBJECT | EXPLORE_FRONTIER
target: exact public object identifier (or destination for EXPLORE_FRONTIER)
entry: exact publicly observed object or reachable destination to start from;
       use target itself when directly accessible. For an unknown prerequisite,
       entry may be a visible object to inspect or a reachable area to search.
public_evidence: nonempty list of short exact quotations from the provided public
       observation, memory, or structured evidence. They support the entry, not a guess.
direction: short explanation connecting this subgoal to the final task or blocker.
completion: OWNED | PUBLIC_PATH_OR_RECIPE | CRAFTED_OR_OWNED | INSPECTED | ARRIVED,
       respectively matching the five types above.
uncertainty: list of explicit unknowns; may be empty only with sufficient evidence.
The controller determines quantities, prerequisites, routes, stopping and budgets.
Use no task-specific assumptions, hidden recipes or invented object identifiers.'''


def validate(data):
    if set(data) != set(FIELDS) or data.get('type') not in KINDS:
        raise ValueError('Invalid subgoal schema or type')
    for key in ('target', 'entry', 'direction', 'completion'):
        if not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 800:
            raise ValueError('Invalid subgoal text: ' + key)
    if data['completion'] != COMPLETION[data['type']]:
        raise ValueError('Completion does not match subgoal type')
    for key in ('public_evidence', 'uncertainty'):
        if not isinstance(data[key], list) or len(data[key]) > 8 or any(
                not isinstance(s, str) or not s.strip() or len(s) > 800 for s in data[key]):
            raise ValueError('Invalid subgoal evidence/uncertainty')
    if not data['public_evidence']:
        raise ValueError('Public evidence required')
