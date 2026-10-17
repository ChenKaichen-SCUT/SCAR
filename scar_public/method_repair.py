"""V12: review method changes against the task and a resource-option portfolio.

The portfolio contains *provisional* recipe routes, not certified quest policies.
A material certificate is deliberately weaker than a task-completion certificate.
Only public observations are used; no engine, score, or evaluator imports.
"""
from collections import deque
import copy
import json
import math
import re

from scar_public.evidence_repair import RepairMemory, RepairController, EvidenceRepairAgent
from scar_public.obligations import base_name, words
from scar_public.causal_model import digest


INSTRUCTION = """
When revising a blocked method, retain the ORIGINAL public task, not just a craft
target. Include task_quote: an exact pending public task. A recipe proves how to
make an output, not that the output serves the task. Inspect descriptions or seek
task feedback when that link is unknown. The word 'equip' in a task need not mean
the equip command: public Stage completed feedback takes precedence.
An alternative may use an observed recipe chain to a task-relevant endpoint.
Include method_endpoint if the proposed craft is an upstream ingredient. This is
a hypothesis until the public evidence supports the endpoint. Do not consume a
scarce ingredient to test an unsupported substitution when it displaces a known
route. Prefer repairing an observed capacity/access condition, or obtaining
information. Stored and dropped materials are not consumed. Original-method
ingredients are never terminal conditions, and a justified alternative can
release them. Never equate a material certificate with full task feasibility.
"""


def task_binding(model, parsed, original=''):
    """Select only an actual pending quotation; ambiguity stays explicit."""
    requested=parsed.get('task_quote') or parsed.get('frame',{}).get('goal_quote','')
    if requested in model.tasks:return requested
    exact=[t for t in model.tasks if original and re.search(r'\b'+re.escape(words(original))+r'\b',t.lower().replace('_',' '))]
    if len(exact)==1:return exact[0]
    # Category reference is used to select the task, not to type an object.
    description=json.dumps(parsed.get('frame',{}))+' '+parsed.get('reasoning','')
    categories=[t for t in model.tasks if any(re.search(r'\b'+c+r'\b',t,re.I) and
                re.search(r'\b'+c+r'\b',description,re.I) for c in ('weapon','armor','container','document'))]
    return categories[0] if len(categories)==1 else ''


def output_support(model, target, task):
    """Evidence for a *necessary task role*, never automatic task achievement."""
    if not task or task not in model.known_tasks:
        return dict(status='UNKNOWN',reason='No uniquely bound public task')
    contract=model.goal_contract(task)
    literals=[p for p in contract['supported_literals'] if base_name(p['item'])==base_name(target)]
    if literals:
        return dict(status='TASK_NAMED_OUTPUT',task=task,output=target,quote=task,literals=literals,
                    sufficiency='Necessary role only; remaining task conditions require public feedback')
    # Public descriptions may explicitly name a category. Lexical item names do
    # not count, and 'not a weapon' must not become positive evidence.
    for line in model.source_lines:
        m=re.match(r'I inspected ([\w-]+): (.*)',line)
        if not m or base_name(m[1])!=base_name(target):continue
        for category in ('weapon','armor','container'):
            if not re.search(r'\b'+category+r'\b',task,re.I):continue
            if re.search(r'\b(?:a|an|the) (?:\w+ ){0,3}'+category+r'\b',m[2],re.I) and not re.search(r'\b(?:not|no|never|cannot|non)\b',m[2],re.I):
                return dict(status='EXPLICIT_CATEGORY_DESCRIPTION',task=task,output=target,quote=line,
                            sufficiency='Category evidence only; command semantics and completion remain unresolved')
    return dict(status='UNKNOWN',task=task,output=target,
                reason='Recipe existence and suggestive names do not establish the task role')


def recipe_chain(model, start, end, max_depth=5):
    """A witnessed numeric dependency path, not a complete executable plan."""
    todo=deque([(start,[]) ]);seen={start}
    while todo:
        item,path=todo.popleft()
        if item==end:return path
        if len(path)>=max_depth:continue
        for output,recipe in sorted(model.recipes.items()):
            if item in recipe['needs'] and output not in seen:
                seen.add(output);todo.append((output,path+[dict(output=output,needs=recipe['needs'],quote=recipe['quote'])]))
    return None


def local_stock(model):
    """Same-site physical resources. No remote remembered stock is certified."""
    state=model.current;stock={};unknown=[]
    for source in ('holding','ground'):
        if state.get(source) is None:unknown.append(source)
        for name,n in (state.get(source) or {}).items():stock[name]=stock.get(name,0)+n
    for name,bag in model.containers.items():
        if not ((state.get('holding') or {}).get(name) or (state.get('equipped') or {}).get(name)):continue
        if bag.get('uncertain_after_craft'):unknown.append('contents of '+name);continue
        for item,n in bag['items'].items():stock[item]=stock.get(item,0)+n
    return stock,unknown


def material_effects(model, action):
    """All three supported quantity rules; no averaging or hidden recipe lookup."""
    m=re.fullmatch(r'craft ([0-9]+(?:\.[0-9]+)?) ([\w-]+)',action)
    if not m or m[2] not in model.recipes:return None
    q=float(m[1]);recipe=model.recipes[m[2]]
    if q<=0 or q!=int(q):return None
    result=[]
    for mode in ('exact','ceil_batch','ceil_per_output'):
        consumption={i:(q*n if mode=='exact' else math.ceil(q*n) if mode=='ceil_batch' else q*math.ceil(n))
                     for i,n in recipe['needs'].items()}
        result.append(dict(mode=mode,consume=consumption,produce={m[2]:q},quote=recipe['quote']))
    return result


def portfolio_check(stock, routes, effects):
    """Exact componentwise reserve check for finite route requirement vectors.

    Disjunction is preserved: it suffices to retain ONE previously stocked route
    in every effect model, not every ingredient of every route simultaneously.
    If none was stocked, increased deficits are reported without claiming loss
    of a feasible task. Accessibility/time/order are outside this certificate.
    """
    before={r['target']:{i:max(0,n-stock.get(i,0)) for i,n in r['needs'].items()} for r in routes}
    viable={name for name,ds in before.items() if not any(ds.values())}
    rows=[]
    for effect in effects:
        after=dict(stock)
        for i,n in effect['consume'].items():after[i]=after.get(i,0)-n
        possible=all(n>=-1e-9 for n in after.values())
        for i,n in effect['produce'].items():after[i]=after.get(i,0)+n
        deficits={r['target']:{i:max(0,n-after.get(i,0)) for i,n in r['needs'].items()} for r in routes}
        retained=[name for name in viable if not any(deficits[name].values())]
        increased={name:{i:d-before[name][i] for i,d in ds.items() if d>before[name][i]+1e-9}
                   for name,ds in deficits.items()}
        rows.append(dict(mode=effect['mode'],craft_materials_present=possible,retained_routes=retained,
                         after_deficits=deficits,increased_deficits={k:v for k,v in increased.items() if v}))
    preserved=bool(viable) and bool(rows) and all(r['craft_materials_present'] and r['retained_routes'] for r in rows)
    return dict(status='MATERIAL_OPTION_PRESERVED' if preserved else 'NO_MATERIAL_PRESERVATION_CERTIFICATE',
                stocked_routes=sorted(viable),before_deficits=before,profiles=rows,
                displaced=bool(viable) and any(not r['retained_routes'] for r in rows),
                qualification='Material availability only; routes may still fail capacity, location, task-role or budget checks')


def route_to(model, destination):
    source=model.current.get('location');todo=deque([(source,[]) ]);seen={source}
    graph=model.routes()
    while todo:
        node,path=todo.popleft()
        if node==destination:return path
        if len(path)>=4:continue
        for command,nxt in sorted(graph.get(node,{}).items()):
            if nxt not in seen:seen.add(nxt);todo.append((nxt,path+['enter '+command]))
    return None


def observed_loss_sites(memory,name):
    """A death during navigation does not locate dropped items at its origin."""
    from scar_public.public_model import state_from_text
    actions={int(i):action for i,action in re.findall(r'^Action (\d+): (.*)$',memory.ledger,re.M)}
    sites=[]
    for i,obs in enumerate(memory.observations):
        if not i or 'lost all items in hand, equipped items, and inventory items at the place I died' not in obs:continue
        action=actions.get(i-1,'')
        if not action.startswith(('attack ','craft ','pick up ','drop ','store ','take out ','inspect ',
                                  'talk to ','equip ','unequip ','write ','wait','look')):continue
        prior=state_from_text(memory.observations[i-1])
        if prior['location'] and ((prior.get('holding') or {}).get(name) or (prior.get('equipped') or {}).get(name)):
            sites.append(prior['location'])
    return sites


def joint_material_completion(model, stock, endpoints, max_expansions=40):
    """A constructive relaxed recipe schedule for all endpoints together.

    Uses worst rounded consumption, subtracts shared inputs, counts existing
    outputs, and rejects cycles/unknown leaves. Capacity, time and access are
    deliberately not certified by this computation.
    """
    remaining=dict(stock);schedule=[];missing={};expansions=[0]
    def obtain(item,quantity,stack):
        held=min(max(0,remaining.get(item,0)),quantity)
        remaining[item]=remaining.get(item,0)-held;need=quantity-held
        if need<=1e-9:return
        expansions[0]+=1
        recipe=model.recipes.get(item)
        if not recipe or item in stack or expansions[0]>max_expansions:
            missing[item]=missing.get(item,0)+need;return
        batches=math.ceil(need)
        for ingredient,n in sorted(recipe['needs'].items()):obtain(ingredient,batches*math.ceil(n),stack+(item,))
        remaining[item]=remaining.get(item,0)+batches-need
        schedule.append(dict(output=item,quantity=batches,quote=recipe['quote']))
    for endpoint,quantity in endpoints:obtain(endpoint,quantity,())
    return dict(status='JOINT_MATERIAL_WITNESS' if not missing else 'NO_JOINT_MATERIAL_WITNESS',
                endpoints=endpoints,schedule=schedule,missing=missing,
                qualification='Constructive material relaxation only, conditional on observed recipe effects; no accessibility or action-budget guarantee')


class MethodMemory(RepairMemory):
    def __init__(self):
        super().__init__()
        self.method_commitment=None
        self.method_reviews=[]
        self.method_enabling=[]
        self.method_probe=None
        self.method_outcomes=[]
        self.method_fallback_attempts=[]


class MethodController(RepairController):
    def method_condition_step(self,text,step):
        m=self.memory;c=m.method_commitment
        if not c or not m.method_enabling:return None
        if step-m.method_enabling[-1]['step']>1:return None
        # If the capability was restored, hand back to the ordinary public
        # dependency planner with the original target, not a surrogate product.
        name=m.method_enabling[-1]['container']
        if (m.model.current.get('equipped') or {}).get(name):
            m.resource_target=c['target'];m.resource_started=step
            return None
        return self.enabling_action(text,step)

    def review_proposal(self,parsed,text):
        review=super().review_proposal(parsed,text)
        if review:
            review['original_task']=task_binding(self.memory.model,parsed,review['action'].split()[-1])
        return review

    def record_rejection(self,review,step):
        target=review['action'].split()[-1]
        if self.memory.method_commitment is None or self.memory.method_commitment['target']!=target:
            self.memory.method_commitment=dict(target=target,task=review.get('original_task',''),created=step,
                recipe=copy.deepcopy(self.memory.model.recipes.get(target)),
                status='PROVISIONAL_ROUTE_NOT_A_COMPLETION_CERTIFICATE')
        super().record_rejection(review,step)

    def prepare_decision(self,text,step):
        # Capture the original method before V11 clears its obstructed target.
        target=self.memory.resource_target
        if target and not self.memory.method_commitment:
            try:
                from scar_public.evidence_repair import enabling_conditions
                from scar_public.resource_competition import ResourceGap
                p=self.ground(text,target);allowed,_=self.bank().query(p)
                if allowed and enabling_conditions(p,allowed[target],'craft 1 '+target)['all_profiles_obstructed']:
                    self.memory.method_commitment=dict(target=target,
                        task=task_binding(self.memory.model,dict(frame=self.memory.frame),target),created=step,
                        recipe=copy.deepcopy(self.memory.model.recipes.get(target)),
                        status='PROVISIONAL_ROUTE_NOT_A_COMPLETION_CERTIFICATE')
            except ResourceGap:pass
        result=super().prepare_decision(text,step)
        m=self.memory;c=m.method_commitment
        if c and (c['task'] in m.model.completed or step-c['created']>=36):
            m.method_outcomes.append(dict(commitment=c,step=step,
                outcome='PUBLIC_COMPLETION' if c['task'] in m.model.completed else 'BOUNDED_REPAIR_EXPIRED'))
            m.method_commitment=None;c=None
        if m.method_probe:
            probe=m.method_probe;m.method_probe=None
            reports=[line for line in text.splitlines() if line.startswith('Stage completed:')]
            m.method_outcomes.append(dict(probe=probe,step=step,completion_reports=reports,
                task_complete=probe['task'] in m.model.completed,
                outcome='PUBLIC_COMPLETION' if probe['task'] in m.model.completed else 'NO_COMPLETION_EVIDENCE'))
        if c:result+='\nOriginal task and provisional resource commitment:\n'+json.dumps(c)+INSTRUCTION
        return result

    def assess_switch(self,parsed):
        c=self.memory.method_commitment;model=self.memory.model;action=parsed['action']
        if not c or not action.startswith('craft '):return None
        target=action.split()[-1]
        if target==c['target']:return None
        task=task_binding(model,parsed,target) or c['task']
        # A truly different named task is a scheduling choice, still audited for
        # interference. Merely replacing the quote by a broad main goal is not.
        endpoint=parsed.get('method_endpoint') or target
        support=output_support(model,endpoint,task);chain=recipe_chain(model,target,endpoint)
        goal_supported=support['status']!='UNKNOWN' and chain is not None
        stock,unknown=local_stock(model);effects=material_effects(model,action)
        routes=[]
        if c.get('recipe'):routes.append(dict(target=c['target'],needs=c['recipe']['needs']))
        # Alternative *same-task* endpoints can release the original recipe's
        # ingredients. A remaining task still retains its resource claim.
        alternative=goal_supported and task==c['task']
        resource=portfolio_check(stock,routes,effects) if effects and routes and not unknown else dict(
            status='UNKNOWN',unknown=unknown,reason='Missing effects, reference recipe, or fresh counts')
        # Explicit pending possessions/crafts are joint commitments, not an
        # independent check that accidentally spends the same input twice.
        other_endpoints=[]
        for pending in model.tasks:
            if pending in (task,c['task']):continue
            for literal in model.goal_contract(pending)['supported_literals']:
                if literal['kind'] in ('held','crafted') and not literal['value']:
                    pair=(base_name(literal['item']),1)
                    if pair not in other_endpoints:other_endpoints.append(pair)
        if not alternative and c.get('recipe'):other_endpoints.append((c['target'],1))
        joint=[]
        for effect in effects or []:
            post=dict(stock)
            for item,n in effect['consume'].items():post[item]=post.get(item,0)-n
            if any(n < -1e-9 for n in post.values()):
                joint.append(dict(mode=effect['mode'],status='NO_JOINT_MATERIAL_WITNESS',reason='Insufficient input totals'));continue
            for item,n in effect['produce'].items():post[item]=post.get(item,0)+n
            joint.append(dict(mode=effect['mode'],**joint_material_completion(model,post,[(endpoint,1)]+other_endpoints)))
        materials=bool(joint) and not unknown and all(r['status']=='JOINT_MATERIAL_WITNESS' for r in joint)
        if alternative:
            # Role + dependency evidence allows switching, not a full policy
            # certificate. Budget/access and terminal feedback are still pending.
            status='TASK_LINKED_METHOD_SWITCH' if materials else 'ALTERNATIVE_RESOURCE_GAP'
        elif not goal_supported:status='UNSUPPORTED_METHOD_SUBSTITUTION'
        elif resource['status']!='MATERIAL_OPTION_PRESERVED' or not materials:status='COMPETING_TASK_RESOURCE_CONFLICT'
        else:status='OTHER_TASK_WITH_MATERIAL_RESERVE'
        return dict(status=status,action=action,original=c,task=task,endpoint=endpoint,
                    task_support=support,recipe_chain=chain,resource=resource,joint_material_witnesses=joint,
                    block=status in ('UNSUPPORTED_METHOD_SUBSTITUTION','COMPETING_TASK_RESOURCE_CONFLICT','ALTERNATIVE_RESOURCE_GAP'))

    def enabling_action(self,text,step):
        """One observed inventory-enabling step; NOT a certified safe navigation.

        Requires an actual prior equip-as-inventory observation and container
        capacity. The executed step is charged and the state is re-read next turn.
        """
        m=self.memory;model=m.model;c=m.method_commitment
        if not c or 'I was attacked' in text or step>=298:return None
        if len(m.method_enabling)>=16:return None
        s=model.current;held=s.get('holding') or {};eq=s.get('equipped') or {};floor=s.get('ground') or {}
        candidates=[]
        for name,bag in model.containers.items():
            proof=next((line for line in model.source_lines if line=='I equipped '+name+' as inventory.'),None)
            if not proof or bag['capacity']<=0 or eq.get(name):continue
            path=None;location=None
            if held.get(name):action='equip '+name;path=[]
            else:
                if floor.get(name):location=s['location']
                else:
                    locs=[loc for loc,v in model.locations.items() if v['objects'].get(name)]
                    # Explicit loss report tells where the attached object was
                    # dropped. This is a historical location, not present access.
                    locs.extend(observed_loss_sites(m,name))
                    paths=[(route_to(model,loc),loc) for loc in locs]
                    paths=[(p,l) for p,l in paths if p is not None]
                    if paths:path,location=min(paths,key=lambda v:len(v[0]))
                if location is None:continue
                if path is None:path=route_to(model,location)
                if path is None:continue
                # A failed pickup at a remembered location must not loop.
                if not path and not floor.get(name):continue
                if model.hand_capacity is not None and sum(held.values())+1>model.hand_capacity:
                    # Dropping preserves physical quantity, but travel/recovery
                    # costs are not ignored: this is a conditional enabling step.
                    options=sorted(held,key=lambda n:(n not in (c.get('recipe') or {}).get('needs',{}),n))
                    if not options:continue
                    action='drop '+options[0]
                else:action=path[0] if path else 'pick up '+name
            signature=digest([action,s.get('location'),held,eq,floor])
            if sum(e['signature']==signature for e in m.method_enabling)>=1:continue
            candidates.append((len(path or []),name,action,proof,signature))
        if not candidates:return None
        _,name,action,proof,signature=min(candidates)
        event=dict(step=step,action=action,container=name,proof=proof,signature=signature,
            qualification='Observed capacity enabler; navigation, survival, contents and task completion remain conditional')
        m.method_enabling.append(event)
        return dict(action=action,decision_source='method_condition_repair',method_enabling=event,
            reasoning='Preserve the task and materials while restoring an observed inventory capability.',
            frame={**m.frame,'goal_quote':c['task'] or m.frame.get('goal_quote','')})

    def finalize_decision(self,parsed,text,step,query,prompt):
        """Bounded review after all inherited proposal/repair paths."""
        c=self.memory.method_commitment
        if not c:return parsed
        report=self.assess_switch(parsed)
        if report:
            self.memory.method_reviews.append(dict(report,step=step))
            parsed['method_review']=report
        # Start constructive condition repair when inherited evidence rejects the
        # original craft, or when a replacement lacks support/preservation.
        rejected=bool(parsed.get('guarded_evidence_review')) or bool(report and report['block'])
        # Continue an initiated, bounded restoration until the known container
        # is equipped or observed feedback invalidates the next step.
        restoring=bool(self.memory.method_enabling) and step-self.memory.method_enabling[-1]['step']<=1
        if (rejected or restoring) and parsed.get('decision_source')!='method_condition_repair':
            enabling=self.enabling_action(text,step)
            if enabling:
                self.memory.resource_target=''
                return {**enabling,'method_review':report,'trigger':parsed['action']}
        if report and report['block']:
            self.memory.resource_target=''
            revised=query(prompt+'\nMethod substitution rejected before consumption:\n'+json.dumps(report)+
                '\nReturn a different, evidenced task path or a non-consuming observation/enabling action. '
                'A recipe is not evidence of the task role. Preserve resources needed by remaining routes.'+INSTRUCTION)
            second=self.assess_switch(revised)
            if second:self.memory.method_reviews.append(dict(second,step=step,revision=True))
            if not second or not second['block']:
                # Do not bypass the old failure guard on this extra revision.
                old=self.review_proposal(revised,text)
                if not old:return {**revised,'method_review':report,'revised_method_review':second}
            # Inspect a presently visible operand; never invent an inspectable
            # output. Repeated fallback observations are bounded by signatures.
            current=self.memory.model.current
            for name in sorted(set(current.get('holding') or {})|set(current.get('ground') or {})):
                key=digest([name,current.get('location')])
                if key not in self.memory.method_fallback_attempts:
                    self.memory.method_fallback_attempts.append(key)
                    return dict(action='inspect '+name,reasoning='Acquire public evidence without consuming the reserved materials.',
                        frame=dict(self.memory.frame),decision_source='method_evidence_observation',method_review=report)
            # No claim that an unsafe proposal is thereby allowed. Release this
            # bounded repair so the general actor can select a new task next turn.
            self.memory.method_commitment=None
            return dict(action='look around',frame=dict(self.memory.frame),decision_source='method_repair_abstention',
                        reasoning='No supported substitution in this bounded repair; seek fresh public context.',method_review=report)
        if report and report['status']=='TASK_LINKED_METHOD_SWITCH':
            self.memory.method_probe=dict(task=report['task'],endpoint=report['endpoint'],action=parsed['action'],step=step)
            # Release old ingredients only for the same anchored task.
            self.memory.method_commitment=None
        return parsed


class MethodRepairAgent(EvidenceRepairAgent):
    def __init__(self,llm,system_prompt):
        super().__init__(llm,system_prompt)
        self.system_prompt+=INSTRUCTION
        self.notebook=MethodMemory();self.resource_controller=MethodController(self.notebook)
