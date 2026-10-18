"""Repair a task-linked prerequisite using a compact public effect request.

Keep the p2 action compiler and budget. Ground references in code, preserve a
public recipe parent, and ask the LLM about methods for its first unmet child.
No learned effect is assumed merely because a method has a valid reference.
"""
import copy
import json

from scar_public.causal_model import digest
from scar_public.continuation import PROTECTED, task_key, threatened
from scar_public.obstacle_repair import mentions
from scar_public.objective_repair import requirement_catalog
from scar_public.plan_repair import PlanRepairAgent, need_key


REQUEST = '''You are proposing a method for ONE unmet prerequisite of the
quoted task, not a new task. Only the public facts below are available.
The program will compile navigation, acquisition and known recipes. Do not
write commands, evidence hashes, quotations, requirement IDs or new recipes.
Return JSON with reasoning, action (copy original for transport only),
and methods (at most two ranked objects). A method has:
{"kind":"site|recipe|container", "site":"listed site or unique exit name",
 "via_item":"optional currently visible item that may enable access",
 "container":"public item for a container method", "why":"causal hypothesis"}.
Omit inapplicable fields. A site method means obtain the missing material at
that site; when the fixed requirement is access, it means reach that destination.
The program fixes this meaning: you never choose whether arrival counts as
success. A proposed enabling object will be acquired first if it is on the
ground, not already held. Recipe uses only the listed recipe for the material.
For a blocked entrance, consider whether a VISIBLE object could change the
access condition; unknown causation is eligible as a bounded trial. For a
missing material, distinguish a source observed to have it, an unvisited source,
and a source just observed empty. Do not assume a one-way route is reversible.
An unrelated reachable room does not repair a material deficit. The relevant
test is whether the material becomes available and is actually acquired.
Your methods list is the method decision. Do not add a separate keep_original
decision: the compiler may need a different first action than your action field.
If no supported or plausible method can change this condition, methods is
empty and the ordinary action is retained. Do not fabricate a remedy.
'''


def site_index(compiler):
    """Readable references, resolving only exact or unique names."""
    entries={}
    for key,site in compiler.catalog['sites'].items():
        if site['location'] and not site.get('origin'):
            entries[site['location']]=(key,site)
    for key,site in compiler.catalog['sites'].items():
        if site['location'] in entries:continue
        label=site.get('origin','')+' -> '+site['name']
        entries.setdefault(label,(key,site))
    return entries


def resolve_site(value,entries):
    if not isinstance(value,str):return None
    if value in entries:return entries[value][0]
    matches=[key for key,site in entries.values() if site['name']==value]
    return matches[0] if len(matches)==1 else None


def compact_request(compiler,plan,frontier,original,text):
    need=frontier['need'];target=need['target'];sites=[]
    for label,(_,site) in site_index(compiler).items():
        path,blocked=compiler.find_route(site)
        sites.append(dict(site=label,exit_name=site['name'],route=path,
            last_observed_target=None if site.get('objects') is None else site['objects'].get(target,0),
            blocked=[r.get('feedback',r.get('reason')) for r in blocked[:3]]))
    terms=[n['target'] for n in frontier['chain']]
    facts=[line for line in compiler.m.source_lines if any(mentions(line,n) for n in terms)]
    return dict(original=original,task=plan['goal_quote'],root_requirement=plan['root_need'],
        unmet=dict(kind=need['kind'],target=target,count=need['count']),
        retained_dependency=[dict(target=n['target'],count=n['count']) for n in frontier['chain']],
        diagnosed_condition=frontier['kind'],current=compiler.m.current,
        latest_feedback=text,sites=sites,observed_recipe=compiler.m.recipes.get(target),
        currently_visible_objects=sorted(set(compiler.m.current.get('holding') or {})|set(compiler.m.current.get('ground') or {})|set(compiler.m.current.get('equipped') or {})),
        containers=compiler.m.containers,past_reports_not_current_inventory=facts[-8:],
        recent_tests=[{k:r.get(k) for k in ('kind','need','site','quantity','failures','step')} for r in compiler.ledger[-4:]],
        scope='Site listings are historical; resource availability and new causal hypotheses require actual observation.')


class EffectRepairAgent(PlanRepairAgent):
    def distinct_goals(self,goal,goals):
        owners=[r for r in self.notebook.progress_tasks.values()
                if goal in {r['quote'],r['source'],*r['aliases']}]
        if len(owners)!=1:return goals
        r=owners[0];aliases={r['quote'],r['source'],*r['aliases']}
        # The actor can quote the public speaker-prefixed source while the
        # registry stores its directive. Do not reserve its own ingredients as
        # if that exact same registered task were a second task. No semantic
        # merging of unrelated tasks is performed.
        return [goal]+[g for g in goals if g not in aliases and g!=goal]

    def root_plan(self,executed,task,step):
        goals=list(dict.fromkeys(r['quote'] for r in self.notebook.progress_tasks.values()))
        quote=executed.get('frame',{}).get('goal_quote','')
        if len(quote)>=12 and any(quote in t for t in self.notebook.observations):goals=list(dict.fromkeys([quote]+goals))
        if not goals:return None
        # Do not mix a failed entrance with every historical task. First select
        # a publicly anchored task, then its explicit output and recipe chain.
        for goal in goals:
            needs=requirement_catalog(self.notebook,executed,[goal],self.continuation)
            roots=[n for n in needs if n['kind']=='resource' and n.get('depth')==0 and mentions(goal,n['target'])]
            if roots:
                need=roots[0]
                return dict(root_need=need,task=task,goal_quote=goal,goals=self.distinct_goals(goal,goals),bindings={},completed=[],started=step)
        # An access-only fragment remains an attempted-method subproblem. Only
        # the currently attempted failed entrance may initiate it; a different
        # actor action cannot be overruled to chase an old destination.
        needs=requirement_catalog(self.notebook,executed,[goals[0]],self.continuation)
        matches=[n for n in needs if n['kind']=='access' and executed['action']=='enter '+n['target']]
        if not matches:return None
        return dict(root_need=matches[-1],task=task,goal_quote=goals[0],goals=self.distinct_goals(goals[0],goals),bindings={},completed=[],started=step)

    def expand_known(self,compiler):
        # Preserve recipe parents without spending a call to restate a known
        # recipe. Existing observed acquisition opportunities take priority.
        for _ in range(4):
            compiled=compiler.compile(self.plan)
            if compiled['status']!='frontier' or compiled['kind']!='CHOOSE_METHOD':return compiled
            need=compiled['need']
            if need['kind']!='resource' or need['target'] not in compiler.m.recipes:return compiled
            self.plan['bindings'][need_key(need)]=dict(kind='recipe',automatic=True,
                hypothesis='Use the publicly observed recipe; missing inputs remain child requirements')
        return compiler.compile(self.plan)

    def ground_methods(self,response,frontier,compiler,task,step):
        if not isinstance(response.get('methods'),list):
            return [],[dict(reasons=['METHOD_SCHEMA_REQUIRED'])]
        entries=site_index(compiler);need=frontier['need'];methods=[];errors=[]
        for raw in response['methods'][:2]:
            if not isinstance(raw,dict):errors.append(dict(reasons=['MALFORMED_METHOD']));continue
            kind=raw.get('kind')
            # Site access is a means of resource acquisition, not a competing
            # terminal condition. Even an old "access" spelling cannot change
            # a resource requirement into arrival success.
            if kind in ('site','source','access'):kind='source' if need['kind']=='resource' else 'access'
            method=dict(kind=kind,need_id=need['id'],goal_quote=self.plan['goal_quote'],hypothesis=raw.get('why'))
            kind=method['kind'];fact=None
            if kind in ('source','access'):
                sid=resolve_site(raw.get('site'),entries)
                if sid is None:errors.append(dict(reasons=['UNKNOWN_OR_AMBIGUOUS_SITE'],site=raw.get('site')));continue
                method['site_id']=sid;fact=compiler.catalog['sites'][sid]['evidence_id']
            elif kind=='recipe':fact=compiler.catalog['recipes'].get(need['target'],{}).get('evidence_id')
            elif kind=='container':
                item=raw.get('container');method['container']=item
                if isinstance(item,str) and item in compiler.catalog['items']:
                    text='Publicly observed object: '+item;fact=digest(text)[:12];compiler.catalog['evidence'][fact]=text
            if raw.get('via_item'):method['via_item']=raw['via_item']
            method['evidence_ids']=[fact] if fact else []
            methods.append(method)
        accepted,rejected=self.parse_methods(dict(keep_original=False,methods=methods),[need],
            [self.plan['goal_quote']],compiler,task,step,self.plan)
        return accepted,errors+rejected

    def finalize_decision(self,executed,obs,step,prompt,query):
        task=task_key(self.notebook);self.observe_use(obs['text'])
        event=dict(step=step,original=executed['action'],changed=False,trigger=None)
        previous=self.observe_plan(obs['text'],task,step)
        if previous:event['previous_repair']=previous
        if self.plan and (self.plan['task']!=task or step-self.plan['started']>=16):
            event['plan_cancelled']='TASK_CHANGED_OR_PLAN_BUDGET';self.plan=None
        if threatened(obs['text']) or executed['action'].startswith(PROTECTED):
            event['reason']='URGENT_ACTION_YIELD';return self.finish(executed,event,task)
        if self.plan and self.plan['root_need']['kind']=='access' and not executed['action'].startswith('enter '):
            # This destination was only an attempted navigation method. It has
            # no supported material/task endpoint authorizing it to suppress
            # the actor's newly available non-navigation behavior.
            self.plan=None;event['plan_cancelled']='ACCESS_METHOD_SUPERSEDED'
            event['reason']='ACCESS_PLAN_YIELDS_TO_NON_NAVIGATION'
            return self.finish(executed,event,task)
        trigger=self.repair_trigger(executed['action'],task)
        active=bool(self.plan)
        if not active and (not trigger or self.repair_mode=='off'):return self.finish(executed,event,task)
        if not active:self.plan=self.root_plan(executed,task,step)
        event['trigger']=trigger or dict(kind='ACTIVE_REQUIREMENT_PLAN')
        if not self.plan:event['reason']='NO_TASK_LINKED_REQUIREMENT';return self.finish(executed,event,task)
        compiler=self.compiler(task,step);compiled=self.expand_known(compiler)
        if compiled['status']=='done':
            event['plan_completed']=True;self.plan=None;return self.finish(executed,event,task)
        if compiled['status']=='ready':return self.commit_compiled(executed,event,compiled,task,step)
        frontier=compiled;event['frontier']=frontier
        if frontier['kind']=='SOURCE_ABSENT':self.remember(frontier,task,step)
        context=digest([task,compiler.context(),frontier])
        limit=12 if active else 10
        if len(self.plan_queries)>=limit:event['reason']='REPAIR_QUERY_BUDGET';return self.finish(executed,event,task)
        if any(q['context']==context and step-q['step']<=6 for q in self.plan_queries):
            event['reason']='RECENT_QUERY_SAME_FRONTIER';return self.finish(executed,event,task)
        packet=compact_request(compiler,self.plan,frontier,executed['action'],obs['text'])
        packet['remaining_actions']=self.max_steps-step
        base=REQUEST+'\nPublic prerequisite state:\n'+json.dumps(packet,ensure_ascii=False)+'\nReturn reasoning, action and methods. An empty methods list retains the ordinary action.'
        response=query(base);self.plan_queries.append(dict(step=step,context=context))
        choices,rejected=self.ground_methods(response,frontier,compiler,task,step)
        event.update(packet=packet,proposal=response,program_rejections=rejected,proposal_calls=1)
        if not choices and rejected and len(self.plan_queries)<limit:
            event.update(initial_proposal=response,initial_rejections=rejected)
            defects=[{k:r[k] for k in ('reasons','site') if k in r} for r in rejected]
            response=query(base+'\nYour proposed methods failed these checks: '+json.dumps(defects)+
                '\nReturn the SAME JSON schema (reasoning, action, methods). Change the method, not the required material. Do not repeat an unsupported reverse route.')
            self.plan_queries.append(dict(step=step,context=context))
            choices,rejected=self.ground_methods(response,frontier,compiler,task,step)
            event.update(proposal=response,program_rejections=rejected,proposal_calls=2)
        if not choices:
            event['reason']='ACTOR_RETAINS_ORIGINAL';return self.finish(executed,event,task)
        self.plan=choices[0]['plan'];compiled=self.expand_known(compiler)
        if compiled['status']=='ready':return self.commit_compiled(executed,event,compiled,task,step)
        event.update(reason='PARENT_RETAINED_CHILD_UNRESOLVED',frontier=compiled)
        return self.finish(executed,event,task)
