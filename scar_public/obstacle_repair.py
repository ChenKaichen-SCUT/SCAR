"""Public missing conditions -> bounded programs -> LLM selection -> observed test.

Programs are experiments, not proofs of goal sufficiency. No private simulator,
score, game identifier or world-specific entity enters this policy.
"""
import copy
import json
import re
from collections import deque

from scar_public.causal_model import digest
from scar_public.continuation import (ContinuationAgent, PROTECTED, feedback_lines,
    nearby, task_key, threatened, visible_options)
from scar_public.public_model import state_from_text


def mentions(text, term):
    normalize = lambda s: re.sub(r'\s+', ' ', s.lower().replace('_', ' ')).strip()
    return bool(term) and re.search(r'(?<!\w)'+re.escape(normalize(term))+r'(?!\w)', normalize(text)) is not None


def options(memory, text, original):
    result = visible_options(memory, text)
    result += ['pick up '+name for name, count in (memory.model.current.get('ground') or {}).items()
               if count > 0 and memory.model.check_action('pick up '+name)['status'] != 'contradicted']
    # Consuming/discarding resources requires the existing joint resource witness.
    result += [c['first_action'] for c in original.get('core_packet', {}).get('candidates', [])]
    return list(dict.fromkeys(result+[original['action']]))


def test_value(test, text):
    s = state_from_text(text); kind, name = test['kind'], test['target']
    if test.get('location') and s['location'] != test['location']: return None
    if kind == 'held':
        return None if s['holding'] is None else s['holding'].get(name, 0) >= test.get('count', 1)
    if kind == 'at':
        return None if s['location'] is None else name in (s['location'], s['location'].split(', ')[-1])
    if kind == 'visible':
        return None if s['ground'] is None else s['ground'].get(name, 0)>0
    if kind == 'content':
        end = r'(?=\n\n|\n(?:I |My |Current |Neighboring |[\w-]+ says:)|\Z)'
        report = re.search(r'^I inspected '+re.escape(name)+r': (.*?)'+end, text, re.M | re.S)
        report = report or re.search(r'^'+re.escape(name)+r' says: (.*?)'+end, text, re.M | re.S)
        # Missing or uninformative text is UNKNOWN, never a negative answer.
        if report and mentions(report[1], test['contains']): return True
    return None


def edge_blocker(evidence, task, location, command, offset=0):
    """Short, revocable deferral at the edge's source, including future edges.

    This is observed-context reuse, not a claim that navigation preserves all
    hidden state. New information/resources, a task change or expiry revokes it.
    """
    current = evidence.current
    if any(current.get(k) is None for k in ('holding', 'equipped')): return None
    for record in reversed(evidence.records):
        if record['action'] != command or record['before'].get('location') != location: continue
        if record['after'].get('location') != location: return None  # newer successful traversal
        if (record['feedback'] and not record['protected'] and record['task'] == task
            and record['epoch_after'] == evidence.epoch
            and 0 <= evidence.step + offset - record['step'] <= 6
            and all(record['before'].get(k) == current.get(k) == record['after'].get(k)
                    for k in ('holding', 'equipped'))):
            return dict(reason='DOWNSTREAM_OBSERVED_FAILURE', location=location, action=command,
                witness_step=record['step'], feedback=record['feedback'], expiry=record['step']+6,
                projected_offset=offset, scope='Same task, information revision and carried resources; temporary heuristic')
    return None


def route_rejections(model, route, evidence, task, start=None, offset=0):
    node = start or model.current.get('location'); rejected = []
    for index, command in enumerate(route):
        if not command.startswith('enter '): break  # do not invent resource effects
        blocker = edge_blocker(evidence, task, node, command, offset+index)
        if blocker: rejected.append(dict(**blocker, plan_index=index, plan=route))
        node = model.edges.get(node, {}).get(command[6:])
        if node is None: break
    return rejected


def known_route(model, destination, evidence, task, start=None, audit=None, offset=0):
    start = start or model.current.get('location'); queue = deque([(start, [])]); seen = {start}
    while queue and len(seen) <= 64:
        node, path = queue.popleft()
        if node and destination in (node, node.split(', ')[-1]): return path
        for exit_name, dest in sorted(model.edges.get(node, {}).items()):
            command = 'enter '+exit_name
            if node == model.current.get('location') and exit_name not in model.current.get('neighbors', []): continue
            blocker = edge_blocker(evidence,task,node,command,offset+len(path))
            if blocker:
                if audit is not None: audit.append(dict(**blocker, candidate_prefix=path+[command], destination=destination))
                continue
            if dest not in seen:
                seen.add(dest); queue.append((dest, path+[command]))
    return None


def information_branches(model, target, place, evidence, task, offset, audit):
    """Presence selects pickup; absence selects a route to a DIFFERENT source.

    Both sources/edges must have been observed. Unknown effects are checked
    again after acting. A request for another free-form reflection is no branch.
    """
    held = model.current.get('holding')
    if held is None or (model.capacity_upper is not None and sum(held.values()) >= model.capacity_upper):
        return None
    alternatives = []
    for other, listing in sorted(model.locations.items()):
        if other == place or not listing['objects'].get(target): continue
        route = known_route(model,other,evidence,task,start=place,offset=offset,audit=audit)
        if route: alternatives.append((len(route),other,route))
    if not alternatives: return None
    _, other, route = min(alternatives)
    return dict(present=dict(action='pick up '+target,plan=['pick up '+target],
                             condition='Observed ground count is positive; recheck carrying capacity'),
                absent=dict(action=route[0],plan=route,source=other,
                            condition='Observed ground count is zero; try the other observed source'),
                probe_location=place, qualification='Decision distinction, not positive expected value or guaranteed completion')


def missing_requirements(memory, original, goals):
    """Backchain public recipes; inputs remain methods, never terminal goals."""
    m = memory.model; holding = m.current.get('holding') or {}; equipped = m.current.get('equipped') or {}
    focus = original.get('core_packet', {}).get('focus') or {}
    roots = [focus['target']] if focus.get('target') in m.recipes else []
    roots += [name for name in m.recipes if any(mentions(q, name) for q in goals)]
    action = original['action']
    if action.startswith(('pick up ', 'craft ')):
        roots.append(action[8:] if action.startswith('pick up ') else action.split()[-1])
    missing = {}; seen = set()
    def visit(name, count, support, depth):
        if depth > 3 or name in seen or holding.get(name, 0)+equipped.get(name, 0) >= count: return
        seen.add(name); missing[name] = dict(count=count,support=support,depth=depth)
        recipe = m.recipes.get(name)
        if recipe:
            for item, amount in recipe['needs'].items(): visit(item,amount,recipe['quote'],depth+1)
    for name in dict.fromkeys(roots):
        visit(name,1,next((q for q in goals if mentions(q,name)),'Actor-selected method: '+str(focus)),0)
    return missing


def repair_programs(memory, original, goals, evidence, task, attempts, access_methods, audit=None):
    if audit is None: audit = []
    m = memory.model; s = m.current; result = []; available = options(memory,evidence.observation,original)
    needed = missing_requirements(memory,original,goals)
    locked = re.match(r'^enter (.+)$',original['action'])
    recent_failure = any(r['action']==original['action'] and r['feedback'] for r in evidence.records[-6:])
    if locked and recent_failure:
        for method in access_methods:
            if method['exit']==locked[1] and not (s.get('holding') or {}).get(method['item']):
                needed.setdefault(method['item'],dict(count=1,depth=0,support=method['support']))
        route = known_route(m,locked[1],evidence,task,audit=audit)
        if route and route[0]!=original['action']:
            result.append(dict(action=route[0],condition='Reach '+locked[1]+' by an observed alternate route',
                test=dict(kind='at',target=route[0][6:]),on_pass=route[1] if len(route)>1 else 'reconsider',
                support=dict(observed_route=route),plan=route,purpose='change',target=locked[1]))
    for name, need in needed.items():
        take = 'pick up '+name
        if (s.get('ground') or {}).get(name,0)>0 and take in available:
            after = (s.get('holding') or {}).get(name,0)+1
            follow = original['action'] if locked and name in [v['item'] for v in access_methods if v['exit']==locked[1]] else 'reconsider'
            result.append(dict(action=take,condition='Acquire missing '+name,target=name,
                test=dict(kind='held',target=name,count=after),on_pass=follow,support=need['support'],purpose='change'))
        for place, listing in sorted(m.locations.items()):
            if place==s.get('location') or not listing['objects'].get(name): continue
            route = known_route(m,place,evidence,task,audit=audit)
            if not route: continue
            branches = information_branches(m,name,place,evidence,task,len(route),audit)
            if not branches:
                audit.append(dict(reason='NO_ACTION_DISTINGUISHING_OUTCOMES',target=name,source=place,plan=route))
                continue
            terminal_test = dict(kind='visible',target=name,location=place)
            test = terminal_test if len(route)==1 else dict(kind='at',target=route[0][6:])
            follow = take if len(route)==1 else route[1]
            result.append(dict(action=route[0],condition='Find missing '+name+' at its last observed location',
                target=name,test=test,on_pass=follow,support=dict(dependency=need['support'],
                observed_location=place,observed_count=listing['objects'][name],route=route),
                plan=route,branches=branches,terminal_test=terminal_test,
                on_fail=branches['absent']['action'] if len(route)==1 else 'reconsider',
                purpose='learn' if len(route)==1 else 'change'))
        # These old proposals have no supported outcome-dependent continuation.
        # Keep explicit rejection diagnostics instead of calling them information.
        for exit_name in s.get('neighbors',[]):
            if exit_name in m.edges.get(s.get('location'),{}): continue
            audit.append(dict(action='enter '+exit_name,target=name,reason='NO_ACTION_DISTINGUISHING_OUTCOMES'))
        for speaker, record in memory.progress_tasks.items():
            speaker = speaker.removesuffix(':main')
            if speaker in nearby(evidence.observation) and record['quote'] in goals:
                audit.append(dict(action='talk to '+speaker,target=name,reason='NO_ACTION_DISTINGUISHING_OUTCOMES'))
    admitted=[]
    for program in result:
        action=program['action'];risk=evidence.assess(action,task)
        if action==original['action'] or action not in available or (risk and risk['kind']=='REPEATED_OBSERVED_FAILURE'): continue
        if test_value(program['test'],evidence.observation) is True: continue
        program.setdefault('on_fail','reconsider')
        if program.get('plan'):
            program['carried_guard']={k:s.get(k) for k in ('holding','equipped')}
        program.update(goal=goals[0],task=task,step=evidence.step)
        scope=digest([task,program['target'],action,s.get('location'),s.get('holding'),s.get('equipped'),program['support']])
        if any(a['scope']==scope and evidence.step-a['step']<=24 for a in attempts): continue
        program['scope']=scope;program['id']=digest(program)[:12]
        if not any(c['scope']==scope for c in admitted): admitted.append(program)
    return admitted[:16]


INSTRUCTION = """
The original method is blocked or cycling. Which CURRENT missing condition prevents the
task, and can one listed program change it or find out how to change it? Choose a program
only if that condition matters to the current task. Recipe inputs are not terminal goals.
Each program is a fallible hypothesis: old locations can be stale and navigation can
change resources or expose danger. Known recent downstream failures have been checked
along the listed route. Arrival at an intermediate room is navigation, NOT information.
Information programs specify distinct concrete continuations for presence and absence;
unknown observations select neither. This is NOT a guarantee that their benefit exceeds
their action cost. A successful first action alone is NOT task progress.
Keep the original action if it is necessary transit, waiting/retrying is better, or none
of the programs solves a relevant obstacle. Do not choose novelty just to avoid failure.
Return ONLY {reasoning: brief reason, action: one command, repair_id: chosen id or null}.
Do not invent a program, task, item, relation or command. No alternatives list is needed.
"""


class ObstacleRepairAgent(ContinuationAgent):
    def __init__(self,llm,system_prompt,repair_mode='repair'):
        super().__init__(llm,system_prompt,repair_mode)
        self.obstacle_pending=None;self.obstacle_attempts=[];self.obstacle_outcomes=[];self.access_methods=[]

    def finalize_decision(self,executed,obs,step,prompt,query):
        evidence=self.continuation;task=task_key(self.notebook)
        event=dict(step=step,original=executed['action'],changed=False,trigger=None)
        if evidence.records and 'I used a key to unlock the path to ' in obs['text'] and not threatened(obs['text']):
            last=evidence.records[-1];before=last['before'].get('holding') or {};after=last['after'].get('holding') or {}
            consumed=[n for n,v in before.items() if after.get(n,0)<v]
            if last['action'].startswith('enter ') and len(consumed)==1:
                method=dict(item=consumed[0],exit=last['action'][6:],support=dict(
                    feedback=[l for l in obs['text'].splitlines() if l.startswith('I used a key')],before_holding=before,after_holding=after))
                if method not in self.access_methods:self.access_methods.append(method)
        pending=self.obstacle_pending;self.obstacle_pending=None
        if pending:
            outcome=None if feedback_lines(obs['text']) else test_value(pending['test'],obs['text'])
            follow=pending['on_pass' if outcome else 'on_fail'] if outcome is not None else 'reconsider'
            result=dict(step=step,contract=pending,outcome=outcome,proposed_continuation=follow,
                        failures=feedback_lines(obs['text']),task_unchanged=pending['task']==task)
            self.obstacle_outcomes.append(result);event['previous_repair']=result
            risk=evidence.assess(follow,task)
            reasons=[]
            if outcome is None: reasons.append('UNOBSERVED_OUTCOME')
            if follow=='reconsider': reasons.append('NO_CONCRETE_CONTINUATION')
            if pending['task']!=task: reasons.append('TASK_CHANGED')
            if threatened(obs['text']) or executed['action'].startswith(PROTECTED): reasons.append('URGENT_ACTION_YIELD')
            if follow not in options(self.notebook,obs['text'],executed): reasons.append('CONTINUATION_NOT_CURRENTLY_AVAILABLE')
            if risk and risk['kind']=='REPEATED_OBSERVED_FAILURE': reasons.append('CONTINUATION_RECENTLY_FAILED')
            if pending.get('carried_guard') and any(evidence.current.get(k)!=v for k,v in pending['carried_guard'].items()):
                reasons.append('CARRIED_STATE_CHANGED')
            rest=pending.get('plan',[])[1:]
            blockers=route_rejections(self.notebook.model,rest,evidence,task)
            branches=pending.get('branches')
            if branches:
                # Revalidate the advertised absence branch as well as the prefix.
                blockers+=route_rejections(self.notebook.model,branches['absent']['plan'],evidence,task,
                    start=branches['probe_location'],offset=len(rest))
            if blockers: reasons.append('DOWNSTREAM_OBSERVED_FAILURE')
            result.update(cancellation_reasons=reasons,downstream_blockers=blockers,admitted=not reasons,
                          decision_distinguishing=pending['test']['kind']=='visible' and bool(branches))
            if not reasons:
                event.update(reason='OBSERVED_TEST_SELECTS_CONTINUATION',changed=follow!=executed['action'])
                if event['changed']:executed=self.replace(executed,follow,pending['goal'],
                    pending['condition']+'; the public intermediate test returned '+str(outcome))
                if outcome and rest:
                    continued=copy.deepcopy(pending);continued['plan']=rest;continued['action']=rest[0]
                    continued['test']=(continued['terminal_test'] if len(rest)==1 and branches
                                       else dict(kind='at',target=rest[0][6:]))
                    continued['on_pass']=rest[1] if len(rest)>1 else (branches['present']['action'] if branches else 'reconsider')
                    continued['on_fail']=branches['absent']['action'] if len(rest)==1 and branches else 'reconsider'
                    continued['purpose']='learn' if len(rest)==1 and branches else 'change'
                    self.obstacle_pending=continued
                return self.finish(executed,event,task)
        trigger=self.repair_trigger(executed['action'],task);event['trigger']=trigger
        if trigger and self.repair_mode!='off' and not evidence.offered(trigger):
            goals=list(dict.fromkeys(r['quote'] for r in self.notebook.progress_tasks.values()))
            quote=executed.get('frame',{}).get('goal_quote','')
            if len(quote)>=12 and any(quote in t for t in self.notebook.observations):goals=list(dict.fromkeys([quote]+goals))
            if goals:
                audit=[]
                programs=repair_programs(self.notebook,executed,goals,evidence,task,self.obstacle_attempts,self.access_methods,audit)
                event['programs']=programs
                event['program_rejections']=audit
                if programs:
                    packet=dict(original=executed['action'],trigger=trigger,goals=goals,programs=programs,
                                previous_repairs=self.obstacle_outcomes[-4:])
                    response=query(prompt+'\nGoal obstacle repair:\n'+json.dumps(packet,ensure_ascii=False)+INSTRUCTION)
                    evidence.mark_offered(trigger);event.update(packet=packet,proposal=response)
                    choice=next((p for p in programs if p['id']==response.get('repair_id') and p['action']==response.get('action')),None)
                    if response.get('action')==executed['action']:event['reason']='ACTOR_RETAINS_ORIGINAL'
                    elif choice:
                        event.update(reason='CONNECTED_TESTABLE_REPAIR',changed=True,contract=choice)
                        self.obstacle_pending=choice;self.obstacle_attempts.append(choice);self.obstacle_attempts=self.obstacle_attempts[-64:]
                        executed=self.replace(executed,choice['action'],choice['goal'],response['reasoning'])
                    else:event['reason']='NO_MATCHING_PROGRAM'
                else:event['reason']='NO_GROUNDED_PROGRAM'
        return self.finish(executed,event,task)

    @staticmethod
    def replace(executed,action,goal,reasoning):
        result=copy.deepcopy(executed);result.update(action=action,reasoning=reasoning)
        result['frame']={**result.get('frame',{}),'goal_quote':goal,'method':reasoning,
                        'expected':'Observe the intermediate condition; task completion remains unconfirmed.'}
        result.pop('resource_target',None)
        return result

    def finish(self,executed,event,task):
        self.continuation.commit(executed['action'],task);event['executed']=executed['action']
        self.continuation_events.append(event);executed['continuation']=event
        if event['changed']:executed['decision_source']='scar_obstacle_repair'
        return executed
