"""V16: persist task obligations and execute bounded, observation-led exploration.

Only public dialogue, observed adjacency and actual transitions enter this module.
Unknown exits are experiments, never certified safe routes or task completion.
"""
import copy
import json
import re
from collections import deque

from scar_public.task_outcome import OutcomeMemory, OutcomeController, TaskOutcomeAgent
from scar_public.intent_repair import task_view
from scar_public.causal_model import digest
from scar_public.obligations import base_name


DIRECTIVE = re.compile(r'^(?:Craft|Make|Produce|Arm|Obtain|Equip|Find|Locate|Defeat|Record|Write|Bring|Deliver|Explore|Speak|Search|Return|Learn|Enter|Head|Attack|Trade|Hold|Investigate|Visit)\b', re.I)


def dialogue_blocks(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r'^([\w-]+) says: (.*)$', line)
        if not match:
            continue
        block = [match[2]]
        for following in lines[i + 1:]:
            if not following.strip() or re.match(r'^(?:I |My |Current |Neighboring |[\w-]+ says:)', following):
                break
            block.append(following)
        yield match[1], '\n'.join(block)


def update_obligations(state, text, step, events):
    # A narrative stage completion only retires the task of its explicitly named
    # next-contact speaker. It does not certify arbitrary other active tasks.
    if re.search(r'^Stage completed[.:]', text, re.M):
        for speaker in re.findall(r'Talk to ([\w-]+) about what to do next\.', text):
            old = state.pop(speaker, None)
            if old:
                events.append(dict(step=step, kind='RETIRED_AFTER_PUBLIC_STAGE_REPORT', speaker=speaker, task=old['quote']))
    for speaker, block in dialogue_blocks(text):
        if re.search(r'\b(?:seem stuck|reminder of your current task)\b', block, re.I):
            if speaker in state:
                events.append(dict(step=step, kind='REMINDER_RETAINS_TASK', speaker=speaker, task=state[speaker]['quote']))
            continue
        lines = [line.strip() for line in block.splitlines()]
        candidates = [line.removeprefix('Main goal: ') for line in lines
                      if DIRECTIVE.match(line) or line.startswith('Main goal: ')]
        if not candidates:
            # Exposition and non-task conversation do not establish retirement.
            continue
        quote = candidates[-1] if not lines[0].startswith('Main goal: ') else candidates[0]
        # A main goal can span multiple explicitly completed stages. Keep it
        # separate from this speaker's current stage instruction.
        key = speaker + ':main' if lines[0].startswith('Main goal: ') else speaker
        previous = state.get(key)
        state[key] = dict(quote=quote, block=block, aliases=list(dict.fromkeys(candidates + [block])),
                              step=step, source=speaker + ' says: ' + block)
        if previous and previous['quote'] != quote:
            events.append(dict(step=step, kind='SUPERSEDED_BY_NEW_INSTRUCTION', speaker=speaker,
                               old=previous['quote'], new=quote, completion_inferred=False))


def context_key(model, text):
    # Reconsider a failed edge after a public clock cell or carried state changes.
    # This finite deferral is not an invariant or an impossibility certificate.
    clock = re.search(r'^Current Time: (\S+ \d+):', text, re.M)
    return digest([model.current.get('holding'), model.current.get('equipped'),
                   clock[1] if clock else None])


def probe_content_key(model, focus, name):
    """Observation indices are not information about the inspected object."""
    document = model.documents.get(name)
    container = model.containers.get(name)
    return digest([focus, name, document.get('text') if document else None,
                   {k:container.get(k) for k in ('items','used','capacity','uncertain_after_craft')} if container else None,
                   [l for l in model.source_lines if l.startswith('I inspected ' + name + ':')]])


def exploration_options(model, goal, attempts, context, limit=64):
    """BFS through observed edges to a task place or an untraversed exit.

Visited locations are not labeled irrelevant: they remain transit nodes and may
be revisited by the actor. No unseen destination is invented from an exit name.
"""
    current = model.current.get('location')
    if not current:
        return []
    graph = model.routes()
    queue = deque([(current, [])]); seen = {current}; options = []
    while queue and len(seen) <= limit:
        location, path = queue.popleft()
        data = model.locations.get(location, {})
        neighbors = model.current.get('neighbors', []) if location == current else data.get('neighbors', [])
        for exit_name in sorted(neighbors):
            edge = location + '\0' + exit_name
            if attempts.get(edge) == context:
                continue
            if any(f['location'] == location and f['action'] == exit_name and
                   len(model.history) - 1 - f['step'] < 6 and
                   f['holding'] == model.current.get('holding') and
                   f['equipped'] == model.current.get('equipped') for f in model.blocked_routes):
                continue
            # A known but recently blocked edge is not a fresh unexplored exit.
            destination = model.edges.get(location, {}).get(exit_name)
            if destination and exit_name not in graph.get(location, {}):
                continue
            if not destination:
                options.append(dict(plan=path + ['enter ' + exit_name], frontier_location=location,
                                    frontier_exit=exit_name, edge=edge,
                                    relevance=int(bool(re.search(r'\b' + re.escape(exit_name.replace('_', ' ')) + r'\b', goal.replace('_', ' '), re.I))),
                                    assumption='The untraversed exit may expose a useful route; reachability and survival are unknown'))
            elif destination not in seen:
                seen.add(destination); queue.append((destination, path + ['enter ' + exit_name]))
    return sorted(options, key=lambda x: (-x['relevance'], len(x['plan']), x['edge']))


class ProgressMemory(OutcomeMemory):
    def __init__(self):
        super().__init__()
        self.progress_tasks = {}
        self.progress_observed = 0
        self.progress_events = []
        self.progress_attempts = {}
        self.progress_pending = None
        self.progress_program = None
        self.progress_decisions = []
        # Navigation remains experimental: task and evidence persistence are the
        # default until whole-game benefits outweigh speculative exploration.
        self.progress_mode = 'observe'
        self.progress_schema = 2

    def refresh_tasks(self):
        for i in range(self.progress_observed, len(self.observations)):
            update_obligations(self.progress_tasks, self.observations[i], i, self.progress_events)
        self.progress_observed = len(self.observations)

    def load(self, state):
        super().load(state)
        if state.get('progress_schema') != 2:
            self.progress_tasks = {}; self.progress_observed = 0
            self.progress_events = []; self.progress_schema = 2
        self.refresh_tasks()


class ProgressController(OutcomeController):
    def bind(self, quote):
        if not isinstance(quote, str) or len(quote) < 12:
            return
        for record in self.memory.progress_tasks.values():
            if quote in record['block'] and quote not in record['aliases']:
                record['aliases'].append(quote)

    def view(self):
        m = self.memory
        records = {str(i): dict(quote=q) for i, q in enumerate(dict.fromkeys(
            q for r in m.progress_tasks.values() for q in r['aliases']))}
        return task_view(m.model, records)

    def prepare_decision(self, text, step):
        m = self.memory; m.refresh_tasks(); self.bind(m.frame.get('goal_quote', ''))
        if m.outcome_probes:
            probe = m.outcome_probes[-1]
            if probe['step'] == step - 1 and m.last_action == probe['action']:
                probe['result_signature'] = probe_content_key(m.model,
                    dict(task=probe['task'],target=probe['target']), probe['action'][8:])
        pending = m.progress_pending
        if pending:
            changed = m.model.current.get('location') != pending['location']
            event = dict(step=step, action=pending['action'], task=pending['task'],
                         kind='OBSERVED_NAVIGATION' if changed else 'NAVIGATION_NOT_CONFIRMED',
                         actual_location=m.model.current.get('location'), previous_location=pending['location'],
                         feedback=[l for l in text.splitlines() if l.startswith(('Cannot ', 'I entered ', 'I used ', 'I was attacked'))])
            m.progress_events.append(event)
            if not changed:
                m.progress_attempts[pending['location'] + '\0' + pending['action'][6:]] = pending['context']
                m.progress_program = None
            elif pending['at_frontier']:
                m.progress_program = None
            m.progress_pending = None
        # V13's one-line registry is overwritten by its own updater. Keep it for
        # checkpoint compatibility; the authoritative view above is independent.
        result = super().prepare_decision(text, step)
        active = [dict(task=r['quote'], source=r['source']) for r in m.progress_tasks.values()]
        return result + ('\nCurrent public task obligations (reminders do not cancel them; completion requires feedback):\n' +
                         json.dumps(active, ensure_ascii=False) if active else '')

    def focus(self, parsed):
        self.bind(parsed.get('task_quote') or parsed.get('frame', {}).get('goal_quote', ''))
        return super().focus(parsed)

    def bounded_probe(self, focus, text, step):
        m=self.memory; model=m.model; s=model.current
        visible=set(s.get('holding') or {})|set(s.get('ground') or {})|set(s.get('equipped') or {})
        names=[n for n in sorted(visible) if base_name(n)==base_name(focus['target'])]
        names += [n for n in sorted(visible) if n in model.containers and model.containers[n].get('uncertain_after_craft')]
        for name in dict.fromkeys(names):
            signature=probe_content_key(model,focus,name)
            if any(signature in (p.get('signature'),p.get('result_signature')) for p in m.outcome_probes):
                continue
            event=dict(step=step,signature=signature,task=focus['task'],target=focus['target'],action='inspect '+name,
                       purpose='Resolve endpoint role or stale accessible contents before committing')
            m.outcome_probes.append(event); m.resource_target=''; self.chosen_step=step
            return dict(action=event['action'],reasoning=event['purpose'],decision_source='task_outcome_observation',
                        outcome_probe=event,frame={**m.frame,'goal_quote':focus['task']})
        return None

    def navigation(self, text, step, proposed=None):
        m = self.memory; model = m.model
        if self.action_mode != 'execute':
            return None
        goal = (proposed or {}).get('frame', {}).get('goal_quote', m.frame.get('goal_quote', ''))
        self.bind(goal)
        if goal not in self.view().tasks or not re.search(r'\b(?:search|explore|find|locate|investigate)\b', goal, re.I):
            m.progress_program = None
            return None
        # This mechanism only replaces movement/waiting, never healing, fighting,
        # collecting a visible goal object, dialogue, or resource consumption.
        if proposed and not proposed['action'].startswith(('enter ', 'wait')):
            return None
        health = re.search(r'^My health is at ([\d.]+)', text, re.M)
        damage = sum(map(float, re.findall(r'I was attacked[^\n]+lost ([\d.]+) HP', text)))
        if health and (float(health[1]) <= max(20, 2 * damage)):
            return None
        program = m.progress_program
        if program and (program['task'] != goal or step - program['created'] >= 8):
            m.progress_program = None; program = None
        if not proposed and not program:
            return None
        context = context_key(model, text)
        options = exploration_options(model, goal, m.progress_attempts, context)
        if not options:
            return None
        if program:
            choice = next((c for c in options if c['edge'] == program['edge']), None)
            if not choice:
                m.progress_program = None
                return None
        else:
            choice = options[0]
            # Do not replace an already unexplored adjacent action with a
            # different arbitrary exit; the actor may know a better goal link.
            if proposed['action'].startswith('enter ') and any(c['plan'] == [proposed['action']] for c in options):
                return None
        if len(choice['plan']) + 1 > min(8, self.max_steps - step):
            return None
        event = dict(step=step, task=goal, proposed=(proposed or {}).get('action'),
                     action=choice['plan'][0], choice=copy.deepcopy(choice),
                     mode=m.progress_mode, claim='Bounded exploration hypothesis, not guaranteed progress or safe completion')
        m.progress_decisions.append(event)
        if m.progress_mode != 'execute':
            return None
        if not program:
            m.progress_program = dict(task=goal, edge=choice['edge'], created=step)
        m.progress_pending = dict(task=goal, action=event['action'], location=model.current['location'],
                                  context=context, at_frontier=model.current['location'] == choice['frontier_location'])
        m.resource_target = ''; m.outcome_focus = None; m.outcome_lease = None
        return dict(action=event['action'], decision_source='task_frontier_execution', progress_choice=event,
                    reasoning='Visit an observed but untraversed exit for the pending search task, checking the next actual observation.',
                    frame={**m.frame, 'goal_quote':goal, 'method':'Test the observed exit ' + choice['frontier_exit'],
                           'expected':'Observe the actual destination or obstruction; an unknown exit does not establish task success.'})

    def method_condition_step(self, text, step):
        return self.navigation(text, step) or super().method_condition_step(text, step)

    def select_proposal(self, parsed, text, step, raw_query, prompt):
        self.bind(parsed.get('task_quote') or parsed.get('frame', {}).get('goal_quote', ''))
        return super().select_proposal(parsed, text, step, raw_query, prompt)

    def finalize_decision(self, parsed, text, step, raw_query, prompt):
        parsed = super().finalize_decision(parsed, text, step, raw_query, prompt)
        if parsed.get('decision_source') == 'task_frontier_execution':
            return parsed
        return self.navigation(text, step, parsed) or parsed


class TaskProgressAgent(TaskOutcomeAgent):
    def __init__(self, llm, system_prompt):
        super().__init__(llm, system_prompt)
        self.notebook = ProgressMemory()
        self.resource_controller = ProgressController(self.notebook)
