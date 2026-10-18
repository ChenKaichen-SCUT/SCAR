"""Persistent requirement plans, compiled public actions, and local revision.

The LLM proposes methods, not command strings. The compiler follows only public
routes/recipes and exposes the first unresolved prerequisite. One actual action
is committed at a time. This is a bounded heuristic, not a complete planner.
"""
import copy
import json
import math
import re
from collections import deque

from scar_public.causal_model import digest, outcome as operation_outcome
from scar_public.continuation import PROTECTED, feedback_lines, task_key, threatened
from scar_public.hypothesis_repair import HypothesisRepairAgent, check_steps, evaluate, required_reserves
from scar_public.objective_repair import requirement_catalog, at_site
from scar_public.obstacle_repair import edge_blocker
from scar_public.public_model import state_from_text


def need_key(need):
    return digest([need['kind'],need['target'],need['count']])[:12]


def child_need(target,count,support):
    n=dict(kind='resource',target=target,count=count,support=support)
    return dict(n,id=need_key(n))


def catalog(memory):
    """Stable references to public facts; no model-authored quotation is accepted."""
    m=memory.model;sites={};facts={}
    def fact(text):
        key=digest(text)[:12];facts[key]=text;return key
    for place,listing in m.locations.items():
        row=dict(location=place,name=place.split(', ')[-1],objects=listing['objects'],
                 neighbors=listing['neighbors'],last_observed=True)
        row['evidence_id']=fact('Observed location '+place+': '+json.dumps(listing,sort_keys=True))
        sites[digest(place)[:12]]=row
    # An explicitly offered exit may be tried although its destination was never
    # visited. No reverse edge or cross-region alias is invented.
    for place,listing in m.locations.items():
        for name in listing['neighbors']:
            dest=m.edges.get(place,{}).get(name)
            key=digest([place,name])[:12]
            sites[key]=dict(location=dest,name=name,origin=place,objects=None,last_observed=bool(dest),
                            evidence_id=fact('Observed exit '+name+' from '+place))
    recipes={name:dict(needs=r['needs'],evidence_id=fact(r['quote'])) for name,r in m.recipes.items()}
    for text in m.source_lines[-40:]:fact(text)
    items=set(m.current.get('holding') or {})|set(m.current.get('ground') or {})|set(m.current.get('equipped') or {})
    for listing in m.locations.values():items.update(listing['objects'])
    return dict(sites=sites,recipes=recipes,items=sorted(items),evidence=facts)


def route(model,site,evidence,task,limit=64,excluded=None):
    """Shortest observed directed route, optionally ending at an offered exit."""
    start=model.current.get('location');queue=deque([(start,[])]);seen={start};blocked=[];excluded=excluded or {}
    def obstruction(node,action,offset):
        return excluded.get((node,action)) or edge_blocker(evidence,task,node,action,offset)
    while queue and len(seen)<=limit:
        node,path=queue.popleft()
        if site['location'] is not None and node==site['location']:return path,blocked
        neighbors=(model.current.get('neighbors',[]) if node==start else model.locations.get(node,{}).get('neighbors',[]))
        if site['location'] is None and node==site['origin'] and site['name'] in neighbors:
            action='enter '+site['name'];reason=obstruction(node,action,len(path))
            if not reason:return path+[action],blocked
            blocked.append(reason)
        # A currently offered exit is a legal trial even when its directed edge
        # has not been traversed. Do not insert a reverse edge or assert that its
        # full destination is known; subsequent compilation checks actual arrival.
        if (site['location'] is not None and site['name'] in neighbors and
            site['name'] not in model.edges.get(node,{}) and
            sum(p.split(', ')[-1]==site['name'] for p in model.locations)==1):
            action='enter '+site['name'];reason=obstruction(node,action,len(path))
            if not reason:return path+[action],blocked
            blocked.append(reason)
        for name,dest in sorted(model.edges.get(node,{}).items()):
            if name not in neighbors:continue
            action='enter '+name;reason=obstruction(node,action,len(path))
            if reason:blocked.append(reason);continue
            if dest not in seen:seen.add(dest);queue.append((dest,path+[action]))
    return None,blocked


class LocalPlanCompiler:
    def __init__(self,memory,evidence,ledger,task,step,uses=()):
        self.memory=memory;self.m=memory.model;self.e=evidence;self.ledger=ledger
        self.task=task;self.step=step;self.uses=uses;self.catalog=catalog(memory)

    def frontier(self,kind,need,chain,**details):
        return dict(status='frontier',kind=kind,need=need,chain=chain,**details)

    def ready(self,action,test,stage,need,chain,**details):
        return dict(status='ready',action=action,test=test,stage=stage,need=need,chain=chain,**details)

    def scoped_failure(self,kind,need,site=None):
        s=self.m.current
        for r in reversed(self.ledger[-32:]):
            if r['task']!=self.task or self.step>r['expiry'] or need_key(r['need'])!=need_key(need) or r['kind']!=kind:continue
            if kind=='SOURCE_ABSENT':
                if r.get('site')!=site:continue
                listing=self.m.locations.get(site,{})
                if listing.get('objects',{}).get(need['target'],0)!=r.get('quantity'):continue
                return r
            if r['context']==self.context():return r
        return None

    def context(self):
        return digest(dict(state=self.m.current,epoch=self.e.epoch))

    def find_route(self,site):
        # A loop through other rooms does not repair the same failed doorway.
        # This finite deferral applies only to the compiled repair, not the base
        # actor. Changed resources or a later successful crossing revoke it.
        excluded={};seen=set();current=self.m.current
        for r in reversed(self.e.records):
            key=(r['before'].get('location'),r['action'])
            if key in seen:continue
            seen.add(key)
            if (not r['action'].startswith('enter ') or not r['feedback'] or r['protected'] or
                r['task']!=self.task or self.step-r['step']>16 or r['after'].get('location')!=key[0]):continue
            if all(current.get(k) is not None and r['before'].get(k)==r['after'].get(k)==current.get(k) for k in ('holding','equipped')):
                excluded[key]=dict(reason='UNREPAIRED_ACCESS_CONDITION',action=r['action'],source=key[0],
                                   witness_step=r['step'],expiry=r['step']+16,feedback=r['feedback'])
        return route(self.m,site,self.e,self.task,excluded=excluded)

    def proposal_view(self):
        public=copy.deepcopy(self.catalog)
        for site in public['sites'].values():
            path,blocked=self.find_route(site)
            site['route_check']=dict(status='available_under_public_checks' if path is not None else 'no_supported_route',
                plan=path,blocked=blocked,scope='Current carried resources; a new access method may change this check. Offered exits can have unverified destinations.')
        return public

    def move(self,path,stage,need,chain,plan,**details):
        action=path[0];test=dict(kind='at',target=action[6:])
        checked=check_steps([dict(action=action,test=test)],self.memory,self.e,self.task,
                            required_reserves(self.memory,plan['goals']),self.uses)
        if checked['errors']:return self.frontier('ACCESS_BLOCKED',need,chain,errors=checked['errors'],**details)
        return self.ready(action,test,stage,need,chain,route=path,remaining_route_length=len(path),**details)

    def capacity(self,need,chain,plan):
        s=self.m.current;held=s.get('holding');cap=self.m.capacity_upper
        if held is None:return self.frontier('INVENTORY_UNKNOWN',need,chain)
        if cap is None or sum(held.values())+1<=cap:return None
        if self.scoped_failure('CAPACITY_FAILED',need):return self.frontier('CAPACITY',need,chain,preserved_source=True)
        # Preserve the source and parent recipe. Only move an unrelated carried
        # item to a publicly inspected, accessible container with observed room.
        protected=required_reserves(self.memory,plan['goals'])
        for n in chain:
            protected[n['target']]=n['count']
            protected.update(self.m.recipes.get(n['target'],{}).get('needs',{}))
        for bag,info in sorted(self.m.containers.items()):
            if info.get('uncertain_after_craft') or not (held.get(bag) or (s.get('equipped') or {}).get(bag)):continue
            if info['capacity']-info['used']<1:continue
            for item,count in sorted(held.items()):
                if item==bag or count<1 or protected.get(item):continue
                action=f'store 1 {item} {bag}'
                return self.ready(action,dict(kind='stored',item=item,container=bag,before=count),
                                  'capacity',need,chain,preserved_source=True)
        return self.frontier('CAPACITY',need,chain,preserved_source=True,holding=held,capacity=cap)

    def compile(self,plan):
        return self.visit(plan,plan['root_need'],[],set())

    def visit(self,plan,need,chain,seen):
        s=self.m.current;held=s.get('holding');chain=chain+[need];key=need_key(need)
        if key in seen or len(chain)>4:return self.frontier('DEPENDENCY_LIMIT',need,chain)
        if need['kind']=='resource' and held is not None and held.get(need['target'],0)>=need['count']:
            return dict(status='done',need=need,chain=chain)
        method=plan['bindings'].get(key)
        if not method and need['kind']=='resource':
            # Compile already observed acquisition opportunities, including
            # recipe inputs, without asking the model to restate trivial facts.
            options=[]
            for site_id,site in self.catalog['sites'].items():
                if not (site.get('objects') or {}).get(need['target']):continue
                if self.scoped_failure('SOURCE_ABSENT',need,site['location']):continue
                path,_=self.find_route(site)
                if path is not None:options.append((len(path),site_id))
            if options:
                _,site_id=min(options)
                method=dict(kind='source',site_id=site_id,hypothesis='Acquire publicly observed material',automatic=True)
                plan['bindings'][key]=method
        if not method:return self.frontier('CHOOSE_METHOD',need,chain)
        kind=method['kind']
        if kind in ('source','access'):
            site=self.catalog['sites'].get(method.get('site_id'))
            if not site:return self.frontier('SOURCE_REFERENCE_CHANGED',need,chain)
            # A visited unknown exit gets a full observed destination after entry.
            if site['location'] is None:
                dest=self.m.edges.get(site['origin'],{}).get(site['name'])
                if dest:site={**site,'location':dest}
            if kind=='source' and self.scoped_failure('SOURCE_ABSENT',need,site['location']):
                return self.frontier('SOURCE_ABSENT',need,chain,site=site['location'],
                                     quantity=self.m.locations.get(site['location'],{}).get('objects',{}).get(need['target'],0))
            here=site['location']==s.get('location') if site['location'] else False
            if not here:
                via=method.get('via_item')
                if via and not (held or {}).get(via) and (s.get('ground') or {}).get(via,0)>=1:
                    space=self.capacity(child_need(via,1,'Proposed access method'),chain,plan)
                    if space:return space
                    return self.ready('pick up '+via,dict(kind='held',target=via,count=1),'access_resource',need,chain)
                path,blocked=self.find_route(site)
                if path is None:return self.frontier('NO_OBSERVED_ROUTE',need,chain,site=site,blocked=blocked)
                if path:
                    return self.move(path,'route',need,chain,plan,site=site)
            if kind=='access':return dict(status='done',need=need,chain=chain)
            ground=s.get('ground');place=s.get('location')
            if ground is None:return self.frontier('VISIBILITY_UNKNOWN',need,chain,site=place)
            if self.scoped_failure('SOURCE_ABSENT',need,place):
                return self.frontier('SOURCE_ABSENT',need,chain,site=place,quantity=ground.get(need['target'],0))
            if ground.get(need['target'],0)<1:
                return self.frontier('SOURCE_ABSENT',need,chain,site=place,quantity=ground.get(need['target'],0))
            space=self.capacity(need,chain,plan)
            if space:return space
            return self.ready('pick up '+need['target'],dict(kind='held',target=need['target'],count=(held or {}).get(need['target'],0)+1),
                              'acquire',need,chain,site=place)
        if kind=='container':
            item=method['container'];visible=set(held or {})|set(s.get('equipped') or {})|set(s.get('ground') or {})
            if item not in visible:
                options=[]
                for site in self.catalog['sites'].values():
                    if not (site.get('objects') or {}).get(item):continue
                    path,_=self.find_route(site)
                    if path:options.append(path)
                if options:return self.move(min(options,key=len),'container_route',need,chain,plan,container=item)
                return self.frontier('CONTAINER_NOT_ACCESSIBLE',need,chain,container=item)
            info=self.m.containers.get(item)
            if info is None or info.get('uncertain_after_craft'):
                if self.scoped_failure('CONTAINER_UNRESOLVED',need):return self.frontier('CONTAINER_UNRESOLVED',need,chain,container=item)
                return self.ready('inspect '+item,dict(kind='contained',container=item,target=need['target'],count=1),
                                  'container_observe',need,chain,container=item)
            if info['items'].get(need['target'],0)<1:
                return self.frontier('CONTAINER_EMPTY',need,chain,container=item)
            space=self.capacity(need,chain,plan)
            if space:return space
            return self.ready(f"take out 1 {need['target']} {item}",
                dict(kind='held',target=need['target'],count=(held or {}).get(need['target'],0)+1),
                'acquire',need,chain,container=item)
        if kind=='recipe':
            recipe=self.m.recipes.get(need['target'])
            if not recipe:return self.frontier('RECIPE_UNKNOWN',need,chain)
            # Craft outputs are NOT presumed held. Acquire an already visible
            # output before spending more inputs on another batch.
            if (s.get('ground') or {}).get(need['target'],0)>=1:
                space=self.capacity(need,chain,plan)
                if space:return space
                return self.ready('pick up '+need['target'],dict(kind='held',target=need['target'],count=(held or {}).get(need['target'],0)+1),'acquire',need,chain)
            for item,count in sorted(recipe['needs'].items()):
                child=child_need(item,count,recipe['quote'])
                if held is None or held.get(item,0)<count:
                    return self.visit(plan,child,chain,seen|{key})
            station=self.m.stations.get(need['target'],{}).get('name')
            if station and not (s.get('ground') or {}).get(station):
                options=[]
                for site in self.catalog['sites'].values():
                    if not (site.get('objects') or {}).get(station):continue
                    path,_=self.find_route(site)
                    if path:options.append(path)
                if not options:return self.frontier('STATION_UNKNOWN_ROUTE',need,chain,station=station)
                path=min(options,key=len)
                return self.move(path,'station_route',need,chain,plan)
            other=[g for g in plan['goals'] if g!=plan['goal_quote']]
            reserve=required_reserves(self.memory,other)
            for item,count in recipe['needs'].items():
                if held[item]-count<min(held[item],reserve.get(item,0)):
                    return self.frontier('OTHER_TASK_RESOURCE',need,chain,item=item)
            if self.scoped_failure('CRAFT_FAILED',need):return self.frontier('CRAFT_FAILED',need,chain)
            action='craft 1 '+need['target']
            return self.ready(action,dict(kind='craft_report',target=need['target']),'craft',need,chain,
                              recipe=recipe,unknown='Public recipe; material accessibility and hidden prerequisites remain empirical')
        return self.frontier('UNSUPPORTED_METHOD',need,chain)


METHOD_INSTRUCTION='''
Repair the METHOD for the fixed unmet requirement. Do not generate route commands
or copy quotations. The compiler uses public directed routes and observed recipes.
Return reasoning, action (copy original for API compatibility), keep_original
(boolean), methods (at most TWO ranked methods). Each method has:
{need_id: listed requirement id, goal_quote: exact listed goal,
 kind:source|recipe|access|container, site_id: public site id for source/access,
 container: public item id for a container method,
 via_item: optional public item hypothesized to enable access,
 hypothesis: brief causal hypothesis, evidence_ids:[1-3 supplied evidence ids]}.
source means obtain the selected material there; its presence may be unverified.
container means inspect an accessible object for the selected material, then
retrieve it only if actual contents support that action. Absence revises the
source; an uninformative inspection does not count as absence or fulfillment.
recipe means use the OBSERVED recipe for the selected material. The compiler
retains parent recipes and asks about a missing ingredient separately. access
is only for a listed access requirement, and must identify that destination.
You may bypass an old route by choosing another source for a MATERIAL requirement.
Do not convert a failed method's destination into a mandatory goal. If a needed
recipe, route, or observation mechanism is unknown, state that limitation; do not
invent a reverse edge, command, recipe or fact. Quotes establish provenance, not
causation. Unknown sources and new access-object hypotheses remain eligible.
A revision changes ONLY the listed unresolved child; keep its parent requirements.
If all methods are worse/unjustified, keep_original=true, methods=[].
'''


class PlanRepairAgent(HypothesisRepairAgent):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.plan=None;self.plan_pending=None;self.plan_ledger=[];self.plan_queries=[]

    def compiler(self,task,step):
        return LocalPlanCompiler(self.notebook,self.continuation,self.plan_ledger,task,step,self.observed_uses)

    def remember(self,result,task,step):
        r=copy.deepcopy(result);r.update(task=task,step=step,expiry=step+24,
            context=self.compiler(task,step).context(),id=len(self.plan_ledger))
        self.plan_ledger.append(r);return r

    def observe_plan(self,text,task,step):
        pending=self.plan_pending;self.plan_pending=None
        if not pending:return None
        test=pending['test'];kind=test['kind']
        if kind=='craft_report':value=operation_outcome(text,pending['action'])=='success' if operation_outcome(text,pending['action']) else None
        elif kind=='stored':
            s=state_from_text(text);line=f"I stored 1 {test['item']} in {test['container']}."
            value=True if line in text and s['holding'] is not None and s['holding'].get(test['item'],0)<=test['before']-1 else None
        else:value=evaluate(test,text)
        failed=feedback_lines(text)
        status='MILESTONE_OBSERVED' if value is True and not failed else 'ACCESS_BLOCKED' if pending['stage'].endswith('route') else 'CRAFT_FAILED' if pending['stage']=='craft' else 'CONTAINER_UNRESOLVED' if pending['stage']=='container_observe' else 'CAPACITY_FAILED' if pending['stage']=='capacity' else 'EXECUTION_UNRESOLVED'
        result=dict(step=step,contract=pending,index=0,execution_outcome=value,outcome=value,
                    requirement_resolved=False,status=status,kind=status,need=pending['need'],
                    failures=failed,admitted=False,decision_distinguishing=False,cancellation_reasons=[])
        if self.plan and self.plan['task']==task:
            compiled=self.compiler(task,step).compile(self.plan)
            result['requirement_resolved']=compiled['status']=='done'
            result['next_frontier']=compiled
            if value is True and not failed:self.plan['completed'].append(dict(action=pending['action'],test=test,step=step))
            else:self.remember(result,task,step)
        self.obstacle_outcomes.append(result);return result

    def parse_methods(self,response,needs,goals,compiler,task,step,parent=None):
        if not isinstance(response.get('keep_original'),bool) or not isinstance(response.get('methods'),list):
            return [],[dict(reasons=['METHOD_SCHEMA_REQUIRED'])]
        plans=[];rejects=[]
        for method in response['methods'][:2]:
            errors=[]
            if not isinstance(method,dict):rejects.append(dict(reasons=['MALFORMED_METHOD']));continue
            need=next((n for n in needs if n['id']==method.get('need_id')),None)
            ids=method.get('evidence_ids');goal=method.get('goal_quote')
            if not need:errors.append('UNKNOWN_REQUIREMENT')
            if goal not in goals:errors.append('UNANCHORED_GOAL')
            if not isinstance(ids,list) or not 1<=len(ids)<=3 or any(not isinstance(i,str) or i not in compiler.catalog['evidence'] for i in ids):errors.append('UNKNOWN_EVIDENCE_REFERENCE')
            if not isinstance(method.get('hypothesis'),str) or not method['hypothesis'].strip():errors.append('MISSING_HYPOTHESIS')
            kind=method.get('kind');site_id=method.get('site_id')
            site=compiler.catalog['sites'].get(site_id) if isinstance(site_id,str) else None
            if kind not in ('source','recipe','access','container'):errors.append('UNSUPPORTED_METHOD')
            elif need and kind=='recipe' and (need['kind']!='resource' or need['target'] not in self.notebook.model.recipes):errors.append('RECIPE_NOT_OBSERVED')
            elif kind in ('source','access'):
                if not site:errors.append('UNKNOWN_SITE_REFERENCE')
                if need and ((kind=='source')!=(need['kind']=='resource')):errors.append('METHOD_REQUIREMENT_MISMATCH')
                if kind=='access' and site and need and need['target'] not in (site['name'],site['location']):errors.append('ACCESS_TARGET_MISMATCH')
            elif kind=='container':
                if not need or need['kind']!='resource':errors.append('METHOD_REQUIREMENT_MISMATCH')
                if method.get('container') not in compiler.catalog['items']:errors.append('UNOBSERVED_CONTAINER')
            if method.get('via_item') and method['via_item'] not in compiler.catalog['items']:errors.append('UNOBSERVED_ACCESS_ITEM')
            if errors:rejects.append(dict(candidate=method,reasons=errors));continue
            plan=copy.deepcopy(parent) if parent else dict(root_need=need,task=task,goal_quote=goal,goals=goals,bindings={},completed=[],started=step)
            plan['bindings'][need_key(need)]=copy.deepcopy(method)
            compiled=compiler.compile(plan)
            if compiled['status']=='frontier' and compiled['kind'] not in ('CHOOSE_METHOD',):
                rejects.append(dict(candidate=method,reasons=[compiled['kind']],frontier=compiled));continue
            plans.append(dict(plan=plan,compiled=compiled))
        return plans,rejects

    def commit_compiled(self,executed,event,compiled,task,step):
        action=compiled['action'];event.update(reason='COMPILED_REQUIREMENT_PLAN',changed=action!=executed['action'],contract=compiled,
            plan=dict(root_need=self.plan['root_need'],goal_quote=self.plan['goal_quote'],bindings=self.plan['bindings'],completed=self.plan['completed'][-8:]))
        if event['changed']:executed=self.replace(executed,action,self.plan['goal_quote'],'Execute a compiled prerequisite; task fulfillment still requires observation')
        self.plan_pending=copy.deepcopy(compiled);self.plan_pending['steps']=[dict(action=action,test=compiled['test'])]
        return self.finish(executed,event,task)

    def finalize_decision(self,executed,obs,step,prompt,query):
        task=task_key(self.notebook);self.observe_use(obs['text'])
        event=dict(step=step,original=executed['action'],changed=False,trigger=None)
        previous=self.observe_plan(obs['text'],task,step)
        if previous:event['previous_repair']=previous
        if self.plan and (self.plan['task']!=task or step-self.plan['started']>=16):
            event['plan_cancelled']='TASK_CHANGED_OR_PLAN_BUDGET';self.plan=None
        urgent=threatened(obs['text']) or executed['action'].startswith(PROTECTED)
        if urgent:
            event['reason']='URGENT_ACTION_YIELD';return self.finish(executed,event,task)
        compiler=self.compiler(task,step);frontier=None
        if self.plan:
            compiled=compiler.compile(self.plan)
            if compiled['status']=='done':event['plan_completed']=True;self.plan=None
            elif compiled['status']=='ready':return self.commit_compiled(executed,event,compiled,task,step)
            else:
                frontier=compiled;event['frontier']=frontier
                if frontier['kind']=='SOURCE_ABSENT':self.remember(frontier,task,step)
        trigger=dict(kind='PLAN_PREREQUISITE_UNRESOLVED',condition=frontier['kind']) if frontier else self.repair_trigger(executed['action'],task)
        event['trigger']=trigger
        if not trigger or self.repair_mode=='off':return self.finish(executed,event,task)
        context=digest([task,compiler.context(),frontier])
        limit=12 if frontier else 10
        if len(self.plan_queries)>=limit:event['reason']='REPAIR_QUERY_BUDGET';return self.finish(executed,event,task)
        if any(q['context']==context and step-q['step']<=6 for q in self.plan_queries):
            event['reason']='RECENT_QUERY_SAME_FRONTIER';return self.finish(executed,event,task)
        goals=list(dict.fromkeys(r['quote'] for r in self.notebook.progress_tasks.values()))
        quote=executed.get('frame',{}).get('goal_quote','')
        if len(quote)>=12 and any(quote in t for t in self.notebook.observations):goals=list(dict.fromkeys([quote]+goals))
        needs=[frontier['need']] if frontier else requirement_catalog(self.notebook,executed,goals,self.continuation)
        if self.plan:goals=[self.plan['goal_quote']]
        if not goals or not needs:event['reason']='NO_COMPUTABLE_REQUIREMENT';return self.finish(executed,event,task)
        packet=dict(original=executed['action'],goals=goals,requirements=needs,frontier=frontier,
            retained_plan=self.plan,public=compiler.proposal_view(),current=self.notebook.model.current,
            trial_evidence=[r for r in self.plan_ledger[-8:] if r['task']==task and step<=r['expiry']],remaining_actions=self.max_steps-step)
        base=prompt+'\nRequirement method repair:\n'+json.dumps(packet,ensure_ascii=False)+METHOD_INSTRUCTION
        response=query(base);self.plan_queries.append(dict(step=step,context=context))
        plans,rejected=self.parse_methods(response,needs,goals,compiler,task,step,self.plan)
        event.update(packet=packet,proposal=response,program_rejections=rejected,proposal_calls=1)
        if not plans and rejected and len(self.plan_queries)<limit:
            event.update(initial_proposal=response,initial_rejections=rejected)
            response=query(base+'\nCorrect only these diagnosed method defects, or keep the original:\n'+json.dumps(rejected,ensure_ascii=False))
            self.plan_queries.append(dict(step=step,context=context));plans,rejected=self.parse_methods(response,needs,goals,compiler,task,step,self.plan)
            event.update(proposal=response,program_rejections=rejected,proposal_calls=2)
        if response.get('keep_original') is not False or not plans:
            event['reason']='ACTOR_RETAINS_ORIGINAL';return self.finish(executed,event,task)
        chosen=plans[0];self.plan=chosen['plan'];compiled=chosen['compiled']
        if compiled['status']=='ready':return self.commit_compiled(executed,event,compiled,task,step)
        # A known recipe may expose an unknown ingredient source. Retain the
        # parent but do not fabricate a move or count this as executed progress.
        event.update(reason='PARENT_RETAINED_CHILD_UNRESOLVED',frontier=compiled)
        return self.finish(executed,event,task)

    def observe_terminal(self,obs):
        super().observe_terminal(obs)
        self.notebook.model.observe(obs['text'])
        self.observe_plan(obs['text'],task_key(self.notebook),self.llm.step+1)
