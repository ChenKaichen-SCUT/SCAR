"""Evidence-scoped plan checking and bounded repair of the selected outcome.

No game names, hidden state, saved paths, provider calls or predicted facts in
the observation ledger. Hypothetical effects are confined to plan validation.
"""
import copy,re
from collections import Counter,deque
try:
    from .feedback_v3r6_core import Ledger as Previous
    from .feedback_v3_core import parts
    from .feedback_v2_core import compact,schema_error
except ImportError:
    from feedback_v3r6_core import Ledger as Previous
    from feedback_v3_core import parts
    from feedback_v2_core import compact,schema_error

HARD={'capacity_conflict','not_held','joint_material_deficit','container_inaccessible','container_full','invalid_schema','invalid_amount'}
class Ledger(Previous):
    def __init__(self):
        super().__init__();self.init_repair_fields()
    def init_repair_fields(self):
        self.repair_audit=[];self.repair_nodes=0;self.repair_feedback=None;self.repair_cache={}

    def independent_checks(self,st,action):
        p=parts(action);hard=[];unknown=[]
        cap=self.capacity_bound(st['loc'],st['equipped'])
        gains=action.startswith(('pick up ','take out '))
        if gains:
            if self.hands_known and cap and sum(st['hands'].values())+1>cap['count']:hard.append('capacity_conflict')
            elif not self.hands_known or cap is None:unknown.append('hand_capacity_unverified')
        if action.startswith('pick up ') and st['ground'].get(action[8:],0)<=0:unknown.append('unobserved_ground_item')
        if p[:2]==['take','out'] and len(p)==4:
            cid=self.canonical_container(p[3]);present=cid in set(st['hands'])|set(st['equipped'])|set(st['ground'])
            if not present:hard.append('container_inaccessible')
            if st['bags'].get(cid,{}).get(p[2],0)<=0:unknown.append('contents_unverified')
        return {'known_conflicts':hard,'unknown_conditions':unknown}

    def _transition(self,st,action):
        check=self.independent_checks(st,action)
        if check['known_conflicts']:return None,check['known_conflicts'][0]
        return super()._transition(st,action)

    def conditional_transition(self,st,action,remembered_only=False):
        nxt,why=self._transition(st,action)
        if nxt is not None:return nxt,why,False
        # Even if the unobserved pickup succeeds, later capacity/material
        # contradictions remain contradictions. This is NOT an observed pickup.
        if why=='unobserved_ground_item' and self.hands_known and action.startswith('pick up '):
            obj=action[8:]
            if remembered_only and self.world.get(st['loc'],{}).get('objects',{}).get(obj,0)<=0:return None,why,False
            hypothetical=copy.deepcopy(st);hypothetical['ground'][obj]=1
            nxt,issue=self._transition(hypothetical,action)
            if nxt is not None:return nxt,why,True
        return None,why,False

    def validate_plan(self,seq):
        st=self._resource_state();verified=0;uncertain=[];checks=[];stop=None;conditional=False
        for i,a in enumerate(seq[:8]):
            check=self.independent_checks(st,a);checks.append({'index':i,'action':a,**check})
            if self.schemas and schema_error(a,self.schemas):nxt,why,assumed=None,'invalid_schema',False
            else:nxt,why,assumed=self.conditional_transition(st,a)
            if nxt is None:
                stop={'index':i,'action':a,'reason':why,'status':'contradicted' if why in HARD else 'requires_observation','conditional_on_prior_success':conditional};break
            if assumed:
                uncertain.append({'index':i,'action':a,'reason':why});conditional=True
            elif not conditional:verified+=1
            st=nxt
            if why and not assumed:
                stop={'index':i,'action':a,'reason':why,'status':'requires_observation','conditional_on_prior_success':conditional};break
        if stop is None and uncertain:
            stop={**uncertain[0],'status':'requires_observation','conditional_on_prior_success':False}
        return {'validated_prefix':verified,'stop':stop,'length':len(seq),'uncertainties':uncertain,'independent_checks':checks,
          'semantics':'Later contradictions may be conditional on all earlier actions succeeding; unknown does not erase independent known constraints.'}

    def gate(self,seq,goal,source):
        c,v=super().gate(seq,goal,source);suffix=[];keep=[]
        for b in c['blockers']:
            if b['kind']=='future_plan_conflict' and b['detail']['index']>0:suffix.append(b['detail'])
            else:keep.append(b)
        c['blockers']=keep
        if suffix:c['warnings'].append({'kind':'suffix_requires_repair','conflicts':suffix,'meaning':'This plan needs repair; this does not prove the first action impossible.'})
        if self.control_checks:self.control_checks[-1].update(blockers=copy.deepcopy(keep),suffix_conflicts=copy.deepcopy(suffix))
        return c,v

    def _select_plan(self,seq,goal,source):
        # An executable prefix is not automatically useful. All action sources
        # must supply a repaired plan or separately justify a single action.
        v=self.validate_plan(seq)
        if v['stop'] and v['stop']['status']=='contradicted':return None
        if source.startswith('local_') and seq[0].startswith('enter '):
            risk=self.repair_risk([seq[0]])
            if risk in ['observed_exit_block_in_destination','observed_damage_exceeds_health_budget']:return None
        return super()._select_plan(seq,goal,source)

    def repair_risk(self,path):
        loc=self.location;damage=0
        for a in path:
            if a.startswith('enter '):
                dest=self.routes.get(loc,{}).get(a)
                if not dest:return 'unverified_route'
                for attempt in self.attempts[-12:]:
                    if attempt.get('location_before')==dest and any('blocked the way out' in x for x in attempt.get('feedback',[])):
                        return 'observed_exit_block_in_destination'
                loc=dest
            damage+=max(self.area_recent.get(loc,[]),default=0)
        if self.hp is not None and damage>=self.hp:return 'observed_damage_exceeds_health_budget'
        return None

    def repair_obligations(self,seq,ti,start):
        # Regress known recipe inputs through the retained suffix. A successful
        # intermediate craft is not evidence that its later inputs are present.
        demand=Counter()
        for a in reversed(seq[ti:]):
            p=parts(a)
            if a.startswith('craft ') and self.needed(a):
                demand[p[-1]]=max(0,demand[p[-1]]-float(p[1]))
                demand.update(self.needed(a))
            elif a.startswith('pick up '):demand[a[8:]]=max(0,demand[a[8:]]-1)
            elif p[:2]==['take','out'] and len(p)==4:demand[p[2]]=max(0,demand[p[2]]-1)
        # A short transfer repair must not recreate the observed material-swap
        # loop by sacrificing another accessible input of the active outcome.
        available=self._available(start);goal=self.work_action()
        reserve={o:min(n,available.get(o,0)) for o,n in self.dependency_requirements(goal).items()} if goal else {}
        for o,n in reserve.items():demand[o]=max(demand[o],n)
        return {o:n for o,n in demand.items() if n>0},reserve

    def repair_plan(self,seq,validation):
        if not self.hands_known:return None,{'reason':'inventory_unverified'}
        stop=validation.get('stop')
        if not stop or stop['status']!='contradicted':return None,{'reason':'no_contradiction'}
        # Repair to the first selected craft outcome, then retain the suffix.
        # Otherwise repair the failing transfer, preserving its remaining plan.
        ti=next((i for i,a in enumerate(seq) if a.startswith('craft ') and self.needed(a)),stop['index'])
        target=seq[ti];suffix=seq[ti+1:];loc=self.location
        for a in seq[:ti]:
            if a.startswith('enter '):
                dest=self.routes.get(loc,{}).get(a)
                if not dest:return None,{'reason':'unverified_route_before_target','target':target}
                loc=dest
        if not (target.startswith(('craft ','pick up ','store ','take out ','equip '))):return None,{'reason':'unsupported_local_repair_target','target':target}
        needed=set(self.needed(target));p=parts(target)
        if target.startswith('pick up '):needed.add(target[8:])
        if p[:2]==['take','out']:needed.add(p[2])
        if p and p[0]=='store':needed.add(p[2])
        for a in seq:needed.update(self.needed(a))
        key=compact([self.step,seq]);cached=self.repair_cache.get(key)
        if cached:return copy.deepcopy(cached)
        start=self._resource_state();requirements,reserve=self.repair_obligations(seq,ti,start);needed.update(requirements)
        q=deque([(start,[])]);seen=set();nodes=0;best_reason='no_supported_bounded_repair'
        while q and nodes<600:
            st,path=q.popleft();sig=compact(st)
            if sig in seen:continue
            seen.add(sig);nodes+=1
            if st['loc']==loc:
                nxt,why,assumed=self.conditional_transition(st,target,remembered_only=True)
                okay=nxt is not None and (why in [None,'terminal_probe_or_execution'] or assumed)
                if target.startswith('craft '):
                    station=self.stations.get(p[-1]);okay=okay and (not station or all(x in st['ground'] for x in station['required']))
                    okay=okay and all(self._available(st).get(o,0)>=n for o,n in requirements.items())
                elif okay:
                    okay=all(self._available(nxt).get(o,0)>=n for o,n in requirements.items())
                if okay:
                    candidate=path+[target]+suffix
                    if len(candidate)<=8 and not self.repair_risk(path+[target]):
                        v=self.validate_plan(candidate)
                        if not v['stop'] or v['stop']['status']!='contradicted':
                            info={'reason':'supported_plan_repair','target':target,'target_location':loc,'nodes':nodes,'original_conflict':stop,'plan':candidate,'required_inputs':requirements,'retained_inputs':reserve}
                            self.repair_nodes+=nodes;self.repair_cache[key]=(candidate,info);return candidate,info
                    elif self.repair_risk(path+[target]):best_reason='repair_exceeds_observed_risk_budget'
            if len(path)>=6:continue
            h=st['hands'];eq=st['equipped'];g=st['ground'];bags=st['bags'];present=set(h)|set(eq)|set(g);options=[]
            for cid in sorted(bags):
                if cid in h and cid not in self.known_non_equippable:options.append('equip '+cid)
                if cid in g:options.append('pick up '+cid)  # Empty known bags can solve capacity.
            for o in sorted(needed):
                if self._available(st).get(o,0)<max(1,self.needed(target).get(o,1),requirements.get(o,0)):
                    if g.get(o,0)>0 or self.world.get(st['loc'],{}).get('objects',{}).get(o,0)>0:options.append('pick up '+o)
                for cid in sorted(bags):
                    if cid in present and bags[cid].get(o,0)>0:options.append(f'take out {o} {cid}')
            for cid in sorted(bags):
                if cid not in present or self.container_limits.get(cid,{}).get('full'):continue
                for o in sorted(h):
                    if o not in bags:options.append(f'store 1 {o} {cid}')
            # Temporary release of a required item is allowed only inside a
            # complete repaired route that reacquires it before the target.
            for o in sorted(h,key=lambda o:(o in needed,o in self.protected_items())):
                if o not in bags:options.append('drop '+o)
            options+=sorted(self.routes.get(st['loc'],{}))
            for a in dict.fromkeys(options):
                if schema_error(a,self.schemas):continue
                nxt,why,assumed=self.conditional_transition(st,a,remembered_only=True)
                if nxt is None or why and not assumed:continue
                # No expansion into a known dangerous route. Unknown safety is
                # not represented as a guarantee; every action is rechecked live.
                if self.repair_risk(path+[a]):continue
                # At uncalibrated locations/equipment do not plan to carry more
                # than the currently observed count bound. This is search-only.
                cap=self.capacity_bound()
                if cap and sum(nxt['hands'].values())>cap['count']:continue
                q.append((nxt,path+[a]))
        self.repair_nodes+=nodes;info={'reason':best_reason,'target':target,'target_location':loc,'nodes':nodes,'original_conflict':stop}
        self.repair_cache[key]=(None,info);return None,info

    def dispatch(self,candidates,goal):
        rejected=[]
        for x in candidates[:3]:
            seq=[a for a in x.get('actions',[])[:6] if isinstance(a,str) and a.strip()] if isinstance(x,dict) else []
            if not seq:continue
            c,v=self.gate(seq,goal,'model_candidate');self.plan_checks.append({'step':self.step,'actions':seq,'validation':v})
            stop=v['stop'];needs=stop and stop['status']=='contradicted'
            repairable=all(b['kind'] in ['future_plan_conflict','observed_hand_capacity'] for b in c['blockers'])
            if needs and repairable and not self.emergency_scope(seq[0]):
                repaired,info=self.repair_plan(seq,v);event={'step':self.step,'original':seq,**info,'repaired':repaired};self.repair_audit.append(event);self.repair_feedback=event
                if repaired:
                    choice=self._select_plan(repaired,goal,'model_plan_locally_repaired')
                    if choice:
                        a,c,d=choice;d.update(rejected=rejected,repair=info);self.interventions.append(d);return a,c,d
            if c['blockers'] or needs:
                reasons=c['blockers'] or [{'kind':'unrepaired_plan_suffix','detail':stop}]
                rejected.append({'action':seq[0],'source':'plan_repair_required' if needs else 'unified_action_gate','blockers':reasons});continue
            selected=self._select_plan(seq,goal,'model_priority_preserved')
            if selected:
                a,c,d=selected;d['rejected']=rejected;self.interventions.append(d);return a,c,d
        self.committed=[];self.queue=[]
        return None,None,{'step':self.step,'selected':None,'source':'no_admissible_model_plan','rejected':rejected}

    def recover_action(self,candidates,goal,rejected):
        # Do not flatten arbitrary suffix actions into an unrelated recovery.
        # A standalone emergency remains admissible independently of its tail.
        for x in candidates:
            seq=x.get('actions',[]) if isinstance(x,dict) else []
            if not seq:continue
            a=seq[0]
            if self.emergency_scope(a):
                choice=self._select_plan([a],goal,'model_emergency_prefix')
                if choice:
                    act,c,d=choice;d['rejected']=rejected;return act,c,d
        # Targeted uncertainty probe, only for a currently accessible known bag.
        for cid,cnt in self.containers.items():
            if cnt['complete'] or cid not in set(self.hands)|set(self.equipped)|set(self.nearby):continue
            choice=self._select_plan(['inspect '+cid],goal,'local_repair_information_probe')
            if choice:
                a,c,d=choice;d['rejected']=rejected;return a,c,d
        return super().recover_action([],goal,rejected)

    def authority_packet(self):
        p=super().authority_packet();r=self.repair_feedback
        p['plan_repair']=None if r is None else {k:r[k] for k in ['step','reason','target','original_conflict','repaired'] if k in r}
        return p

    def to_dict(self):
        p=super().to_dict();p['v3r7_repair_audit']={'events':self.repair_audit,'nodes':self.repair_nodes};return p
