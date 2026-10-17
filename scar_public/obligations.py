"""Observed obligations: conservative goals, resource dependencies, and real probes.

This is a partial public-text model. Plans are conditional and only their first
action is executed. No environment/evaluator objects are available in this module.
"""
import copy
import heapq
import itertools
import json
import math
import re
import time

from scar_public.public_model import PublicModel


def base_name(name):
    return re.sub(r"_\d+$", "", name)


def words(name):
    return base_name(name).replace("_", " ").lower()


def explicit_role_bindings(goal, source_lines):
    """Narrow lexical role binding; unsupported aliases/coreference remain unresolved."""
    match=re.search(r'\b(?:record|write|inscribe|copy) (?:the |a |an )?(.+?) (?:on|onto|in|into)\b',goal,re.I)
    if not match:return []
    role=match[1].strip()
    pattern=re.compile(r'\b'+re.escape(role)+r'\s*(?:is\s+|:\s*|=\s*)?[\'"`]?([A-Za-z0-9][\w-]{2,})',re.I)
    found=[]
    for line in source_lines:
        for m in pattern.finditer(line):
            value=m[1]
            # This narrow branch binds literal identifiers, not natural-language clauses.
            if not (value.isupper() or '-' in value or '_' in value or any(c.isdigit() for c in value)):continue
            if not any(x['value']==value for x in found):
                found.append({'value':value,'quote':line,'role':role,'binding':'explicit role followed by literal identifier'})
    return found


class ExecutionModel(PublicModel):
    def __init__(self):
        super().__init__()
        self.qualitative_recipes = {}
        self.crafted = []
        self.transitions = []
        self.write_probe = None
        self.semantic_trials = []
        self.append_documents = {}
        self.blocked_routes = []
        self.new_outputs = []
        self.writing_tools = []
        self.recipe_counterexamples = []

    def observe(self, text, last_action=None):
        before = copy.deepcopy(self.current)
        before_bags=copy.deepcopy(self.containers)
        before_docs = copy.deepcopy(self.documents)
        before_index = len(self.history)-1
        super().observe(text, last_action)
        if last_action and last_action.startswith('craft ') and 'Do not have sufficient amount of necessary ingredients' in text:
            target=last_action.split()[-1];recipe=self.recipes.get(target)
            held=before.get('holding') or {};equipped=before.get('equipped') or {}
            if recipe and before.get('holding') is not None:
                counts={n:held.get(n,0) for n in recipe['needs']}
                for name,bag in before_bags.items():
                    if (held.get(name) or equipped.get(name)) and not bag.get('uncertain_after_craft'):
                        for n in counts:counts[n]+=bag['items'].get(n,0)
                if all(counts[n]>=q for n,q in recipe['needs'].items()):
                    self.recipe_counterexamples.append({'target':target,'location':before.get('location'),
                        'counts':counts,'recipe':copy.deepcopy(recipe['needs']),'step':len(self.history)-1,
                        'meaning':'The observed-input model predicted enough ingredients, but execution contradicted it; an omitted condition or wrong public model remains possible.'})
        for target, ingredients in re.findall(r"([\w-]+) \(made of ([^()]+)\)", text):
            self.qualitative_recipes[target] = ingredients.split(", ")
        if last_action and last_action.startswith("craft ") and "I successfully crafted " in text:
            self.crafted.append(last_action.split()[-1])
            target=last_action.split()[-1]
            for key in ('holding','ground'):
                for name,count in (self.current.get(key) or {}).items():
                    if base_name(name)==target and count>(before.get(key) or {}).get(name,0):
                        self.new_outputs.append(name)
        if (last_action and last_action.startswith('enter ') and before.get('location')==self.current.get('location') and
                re.search(r'Cannot enter|door is locked',text)):
            self.blocked_routes.append({'location':before.get('location'),'action':last_action[6:],
                'holding':before.get('holding'),'equipped':before.get('equipped'),'step':len(self.history)-1,
                'feedback':[l for l in text.splitlines() if 'Cannot enter' in l or 'door is locked' in l]})
        if last_action:
            self.transitions.append({"action":last_action,"before":before,"after":copy.deepcopy(self.current),
                "feedback":[l for l in text.splitlines() if l.startswith(("Cannot ","I entered ","I successfully ","Stage completed:"))]})
        if last_action and last_action.startswith("write "):
            payload, document = last_action[6:].rsplit(" ",1)
            self.new_outputs=[n for n in self.new_outputs if n!=document]
            if 'I wrote on '+document+':' in text:
                self.writing_tools=list(dict.fromkeys(self.writing_tools+[n for n in (before.get('holding') or {}) if n!=document]))
            old = before_docs.get(document)
            if old and old['observed_at'] == before_index and old['text'] and "I wrote on " in text:
                self.write_probe = {"document":document,"before":old['text'],"payload":payload,
                    "step":len(self.history)-1,"action":last_action,"status":"awaiting_inspection",
                    "hypotheses":{"append":old['text']+payload,"replace":payload},
                    "preconditions":{"fresh_prewrite_inspection":True,"write_accepted":True},
                    "qualification":"Only this accepted write on this document; omitted formatting rules remain possible."}
        if self.write_probe and last_action == "inspect "+self.write_probe['document']:
            trial = self.write_probe
            doc = self.documents.get(trial['document'])
            if doc and doc['observed_at'] == len(self.history)-1:
                trial['observed'] = doc['text']
                trial['consistent'] = [h for h,p in trial['hypotheses'].items() if p == doc['text']]
                trial['status'] = 'observed' if trial['consistent'] else 'neither_prediction'
                if trial['consistent'] == ['append']:
                    self.append_documents[trial['document']] = copy.deepcopy(trial)
            else:
                trial['status'] = 'unobserved'
                trial['consistent'] = []
            self.semantic_trials.append(trial)
            self.write_probe = None

    def entities(self):
        result = set(self.recipes) | set(self.qualitative_recipes)
        for s in [self.current]+[{"ground":d['objects']} for d in self.locations.values()]:
            for k in ('holding','ground','equipped'):
                result.update((s.get(k) or {}).keys())
        for recipe in self.recipes.values(): result.update(recipe['needs'])
        return result

    def goal_contract(self, quote):
        """Only narrow explicit grammar creates predicates; other semantics stay open.

        There is no LLM-provided condition list to silently promote. Exact public
        completion remains the achievement criterion, even if all literals hold.
        """
        grounded=bool(quote) and any(quote in line for line in self.source_lines)
        text = quote.lower().replace('_',' ') if grounded else ''
        mentions = [n for n in sorted(self.entities()) if re.search(r'\b'+re.escape(words(n))+r'\b',text)]
        literals = []
        for name in mentions:
            noun = re.escape(words(name))
            explicit_craft = bool(re.search(r'\b(?:craft|make|produce) (?:a |an |one )?'+noun+r'\b',text))
            if explicit_craft:
                literals.append({'kind':'crafted','item':name,'value':base_name(name) in self.crafted})
            if (re.search(r'\b(?:hold|carry) (?:a |an |the )?'+noun+r'\b',text) or
                    (explicit_craft and re.search(r'\bhold it in your hands\b',text))):
                inv = self.current.get('holding')
                literals.append({'kind':'held','item':name,'value':None if inv is None else inv.get(name,0)>=1})
            if re.search(r'\bequip (?:a |an |the )?'+noun+r'\b',text):
                eq = self.current.get('equipped')
                literals.append({'kind':'equipped','item':name,'value':None if eq is None else eq.get(name,0)>=1})
        return {'public_goal_quote':quote,'source_grounded':grounded,'supported_literals':literals,
                'achievement':'explicit public completion only',
                'confirmed':quote in self.completed,
                'unresolved':'Unexpressed task meaning remains unknown; literals are necessary candidate checks, not a sufficient definition.',
                'method_ingredients_are_not_terminal_conditions':True}

    def relevant_repetition(self, action):
        """Repeat warning uses observed inventory/location; health/time can still matter."""
        keys = ('location','holding','equipped','ground')
        return sum(t['action']==action and all(t['before'].get(k)==self.current.get(k) for k in keys)
                   for t in self.transitions[-16:])

    def routes(self):
        # Previously successful edges are historical. Current visible adjacency wins.
        graph = copy.deepcopy(self.edges)
        current = self.current.get('location')
        if current in graph and self.current.get('neighbors'):
            graph[current] = {a:d for a,d in graph[current].items() if a in self.current['neighbors']}
        for failure in self.blocked_routes:
            # A short conditional exclusion, not a permanent impossibility claim.
            if (len(self.history)-1-failure['step']<6 and failure['holding']==self.current.get('holding') and
                    failure['equipped']==self.current.get('equipped')):
                graph.get(failure['location'],{}).pop(failure['action'],None)
        return graph

    def dependency_view(self, target):
        seen = set()
        def visit(item, depth=0):
            if item in seen or depth>7: return {'item':item,'unresolved':'cycle or depth bound'}
            seen.add(item)
            recipe = self.recipes.get(item)
            inputs = recipe['needs'] if recipe else {n:None for n in self.qualitative_recipes.get(item,[])}
            result = {'item':item,'numeric_recipe':recipe,'known_station':self.stations.get(item),
                'last_seen_at':[loc for loc,s in self.locations.items() if any(base_name(n)==item for n in s['objects'])],
                'inputs':[{'quantity':count,'dependency':visit(n,depth+1)} for n,count in inputs.items()]}
            seen.remove(item)
            return result
        return visit(target)

    def acquisition(self, target, max_nodes=3500, seconds=1.0, fresh=False, prune_impossible=None):
        """Bounded weighted search over known locations, recipes, storage and counts.

        Unknown recipe effects/station requirements remain conditional. A successful
        observed edge is not a promise that the route will remain open. Every action
        is followed by real observation; no simulated state is accepted as evidence.
        """
        if getattr(self, 'node_budget_only', False): seconds = float('inf')
        if prune_impossible is None:prune_impossible=getattr(self,'acquisition_pruning',False)
        self.last_acquisition_pruning={'enabled':prune_impossible,'capacity_removed':[],
                                       'target_unreachable_in_relaxation':False}
        current = self.current
        if not target or current.get('holding') is None or current.get('ground') is None:
            return {'status':'unknown','reason':'missing target or current visibility'}
        held, ground, equipped = current['holding'],current['ground'],current.get('equipped') or {}
        aliases = [n for n in set(held)|set(ground) if base_name(n)==target and
                   (not fresh or n in self.new_outputs or self.documents.get(n,{}).get('text')=='')]
        if any(held.get(n,0)>=1 for n in aliases): return {'status':'acquired','plan':[]}
        if self.hand_capacity is None: return {'status':'unknown','reason':'capacity not yet established'}
        cap = self.hand_capacity
        for name in aliases:
            if ground.get(name,0)>=1 and sum(held.values())+1<=cap:
                return {'status':'candidate','plan':['pick up '+name],'target':target}
        # Refresh carried container contents after crafting before using them in a plan.
        for name,b in self.containers.items():
            if (held.get(name) or equipped.get(name)) and b.get('uncertain_after_craft'):
                return {'status':'observe_container','plan':['inspect '+name],'target':target}
        closure = {target}
        for _ in range(7):
            more = {n for t in closure for n in self.recipes.get(t,{}).get('needs',{})}
            if more <= closure: break
            closure |= more
        if len(closure)>20: return {'status':'unknown','reason':'dependency search bound'}
        recipes = {n:r['needs'] for n,r in self.recipes.items() if n in closure}
        # Repeated counterexamples suspend automatic use of that recipe model.
        # The actor may still propose a new, justified test. This is not a global
        # action ban or a conclusion that the task is impossible.
        unresolved={n for n,r in recipes.items() if len({json.dumps((c['location'],c['counts']),sort_keys=True)
            for c in self.recipe_counterexamples if c['target']==n and c['recipe']==r})>=2}
        recipes={n:r for n,r in recipes.items() if n not in unresolved}
        graph = self.routes()
        start_loc = current.get('location')
        locations = sorted(self.locations)
        if start_loc not in locations: return {'status':'unknown','reason':'location unavailable'}
        # Include only one already observed accessible container per candidate search.
        bags = [(n,b) for n,b in self.containers.items() if not b.get('uncertain_after_craft') and
                (held.get(n) or equipped.get(n) or ground.get(n))]
        bagname, bag = bags[0] if bags else (None,{'items':{},'capacity':0,'used':0})
        if prune_impossible:
            # Necessary condition in THIS finite acquisition model, not a claim
            # about the real game: crafts draw from hand plus this one bag. This
            # optimistic bound even grants the full hand and bag capacities,
            # ignoring attachment/background costs. A recipe exceeding it cannot
            # occur in any searched state. Other unknown containers remain a
            # paid discovery option through arrange() below.
            total_capacity=max(cap,sum(held.values()))+max(bag['capacity'],sum(bag['items'].values()))
            removed=[n for n,r in recipes.items() if sum(round(v*1000) for v in r.values())>total_capacity*1000]
            self.last_acquisition_pruning.update(capacity_removed=removed,optimistic_accessible_capacity=total_capacity)
            recipes={n:r for n,r in recipes.items() if n not in removed}
            reachable={start_loc};todo=[start_loc]
            while todo:
                loc=todo.pop()
                for dest in graph.get(loc,{}).values():
                    if dest in locations and dest not in reachable:reachable.add(dest);todo.append(dest)
            # Delete-relaxed type reachability deliberately ignores finite stock,
            # ordering, capacity needed to carry the bag, and recipe competition.
            # Absence even here certifies absence from the concrete search graph.
            possible={n for n,v in held.items() if v>0}|{n for n,v in bag['items'].items() if v>0}
            for loc in reachable:possible.update(n for n,v in self.locations[loc]['objects'].items() if v>0)
            changed=True
            while changed:
                changed=False
                for output,needs in recipes.items():
                    station=self.stations.get(output,{}).get('name')
                    required={n for n,v in needs.items() if round(v*1000)>0}
                    if output not in possible and required<=possible and (not station or any(self.locations[l]['objects'].get(station) for l in reachable)):
                        possible.add(output);changed=True
            if target not in possible:
                self.last_acquisition_pruning.update(target_unreachable_in_relaxation=True,
                    reachable_locations=sorted(reachable),relaxed_types=sorted(possible))
                local=self.arrange(target)
                if local.get('plan') and local.get('status')=='capacity_discovery':
                    return {**local,'target':target,'search_nodes':0}
                return {'status':'unknown','reason':'no plan within observed dependency/location model and bounds',
                        'search_nodes':0,'dependency':self.dependency_view(target),
                        'automatic_recipe_models_suspended_pending_new_evidence':sorted(unresolved),
                        'counterexamples':self.recipe_counterexamples[-4:]}
        names = sorted(closure | set(held) | ({bagname} if bagname else set()))
        ni = {n:i for i,n in enumerate(names)}; li = {l:i for i,l in enumerate(locations)}
        # Observed quantities use decimal fractions; 1/1000 is an explicit adapter bound.
        scale=1000
        def vector(d): return tuple(round(d.get(n,0)*scale) for n in names)
        h0=vector(held); b0=vector(bag['items'])
        all_ground=tuple(vector(self.locations[l]['objects']) for l in locations)
        e0=bool(bagname and equipped.get(bagname))
        start=(li[start_loc],h0,b0,e0,all_ground)
        recipe_indices = {ni[n]:{ni[k]:round(v*scale) for k,v in r.items()} for n,r in recipes.items()}
        station_indices = {ni[n]:self.stations.get(n,{}).get('name') for n in recipes}
        required_limit = {n:scale for n in names}
        # Bound excess carrying, not world counts; do not create or discard resources.
        for r in recipes.values():
            for n,v in r.items(): required_limit[n]=max(required_limit[n],math.ceil(v)*scale*2)
        serial=itertools.count(); queue=[]; best={start:0}; deadline=time.monotonic()+seconds
        def heuristic(state):
            loc,h,b,e,gs=state
            attached=e or bool(bagname and h[ni[bagname]])
            def need(i, amount, trail):
                have=h[i]+(b[i] if attached else 0)
                missing=max(0,amount-have)
                if not missing:return 0
                candidates=[]
                if gs[loc][i]>=missing:candidates.append(math.ceil(missing/scale))
                if any(g[i]>=missing for g in gs):candidates.append(3+math.ceil(missing/scale))
                if i in recipe_indices and i not in trail:
                    candidates.append(2+sum(need(j,c,trail|{i}) for j,c in recipe_indices[i].items()))
                return min(candidates) if candidates else 12
            return need(ni[target],scale,set())
        heapq.heappush(queue,(heuristic(start)*2,next(serial),0,start,[]))
        while queue and len(best)<max_nodes and time.monotonic()<deadline:
            _,_,cost,state,path=heapq.heappop(queue)
            if cost!=best.get(state):continue
            loc,h,b,e,gs=state
            if h[ni[target]]>=scale:
                return {'status':'candidate','plan':path,'target':target,'search_nodes':len(best),
                    'assumptions':['observed routes remain open','unit capacity model','recipe yields one output on ground',
                                   'carried container inputs are accessible; unknown stations may block craft']}
            if len(path)>=28:continue
            attached=e or bool(bagname and h[ni[bagname]])
            options=[]
            def move_item(i,src,dst,amount=scale):
                hh=list(h); bb=list(b); gg=[list(x) for x in gs]
                stores={'hand':hh,'bag':bb,'ground':gg[loc]}
                stores[src][i]-=amount;stores[dst][i]+=amount
                return (loc,tuple(hh),tuple(bb),e,tuple(tuple(x) for x in gg))
            for action,dest in graph.get(locations[loc],{}).items():
                if dest in li: options.append(((li[dest],h,b,e,gs),'enter '+action))
            for i,n in enumerate(names):
                carried=h[i]+(b[i] if attached else 0)
                if gs[loc][i]>=scale and sum(h)+scale<=cap*scale and (n in closure or n==bagname) and carried<required_limit[n]:
                    options.append((move_item(i,'ground','hand'),'pick up '+n))
                if h[i]>=scale:
                    options.append((move_item(i,'hand','ground'),'drop '+n))
                    if bagname and n!=bagname and attached and bag['used']*scale-sum(b0)+sum(b)+scale<=bag['capacity']*scale:
                        options.append((move_item(i,'hand','bag'),f'store 1 {n} {bagname}'))
                    if n==bagname and not e and not equipped:
                        hh=list(h);hh[i]-=scale
                        options.append(((loc,tuple(hh),b,True,gs),'equip '+n))
                if bagname and attached and b[i]>=scale and sum(h)+scale<=cap*scale and n in closure:
                    options.append((move_item(i,'bag','hand'),f'take out 1 {n} {bagname}'))
            for output,needs in recipe_indices.items():
                station=station_indices[output]
                if station and not self.locations[locations[loc]]['objects'].get(station):continue
                if h[output]+b[output]+gs[loc][output]>=required_limit[names[output]]:continue
                if not all(h[j]+(b[j] if attached else 0)>=amount for j,amount in needs.items()):continue
                projected={names[j]:(h[j]+(b[j] if attached else 0))/scale for j in needs}
                if any(c['target']==names[output] and c['location']==locations[loc] and c['counts']==projected and
                       c['recipe']==self.recipes[names[output]]['needs'] for c in self.recipe_counterexamples):continue
                hh=list(h);bb=list(b);gg=[list(x) for x in gs]
                for j,amount in needs.items():
                    used=min(hh[j],amount);hh[j]-=used;bb[j]-=amount-used
                gg[loc][output]+=scale
                candidate=(loc,tuple(hh),tuple(bb),e,tuple(tuple(x) for x in gg))
                options.append((candidate,'craft 1 '+names[output]))
            for successor,action in options:
                # Exact repeated failure is local evidence, not a global recipe ban.
                if not path and self.relevant_repetition(action)>=2 and action.startswith('craft '):continue
                nxt=cost+1
                if nxt<best.get(successor,math.inf):
                    best[successor]=nxt
                    heapq.heappush(queue,(nxt+2*heuristic(successor),next(serial),nxt,successor,path+[action]))
        local=self.arrange(target)
        if local.get('plan') and local.get('status')=='capacity_discovery':
            return {**local,'target':target,'search_nodes':len(best)}
        return {'status':'unknown','reason':'no plan within observed dependency/location model and bounds',
                'search_nodes':len(best),'dependency':self.dependency_view(target),
                'automatic_recipe_models_suspended_pending_new_evidence':sorted(unresolved),
                'counterexamples':self.recipe_counterexamples[-4:]}
