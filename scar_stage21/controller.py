"""Frozen S1/P1/P3 execution plus public-entry repairs and isolated ETBR.

No world, task catalogue, evaluation truth or historical trajectories are inputs.
Stage20 persistent material/workstation intents are replaced by one bounded probe.
"""
import copy
import re
from scar.io import digest
from scar_sequence.planner import q
from scar_stage17.budget_adapter import Budget100Controller
from scar_stage20.controller import Controller20
from scar_stage16.controller import BaselineController
from scar_v3.state import parse_action
from .config import NORMAL_EXPLORATION, MAX_PLANNING_CALLS, MAX_PROBE_ACTIONS, MAX_TRANSIT_STEPS
from .public import public_route, access
from . import knowledge
from .recovery import Recovery, blocker_id


class Controller21(Controller20):
    def __init__(self):
        super().__init__()
        self.etbr21=Recovery()
        self.initial_evidence21=False
        self.blocker_key21='initial'
        self.probe21=None
        self.probe_log21=[]
        self.probe_attempts21={}
        self.probe_events21=[]
        self.transition21={}
        self.selection21=None
        self.engineering21=[]
        self.intent20=self.suspended20=None

    def context(self, action):
        value=super().context(action)
        if parse_action(action).verb=='enter':
            value['blocker_scope']=self.blocker_key21
        return value

    def public_entries(self):
        t=self.table;loc=t.state.get('location')
        known=set(t.places)|{n for ns in t.links.values() for n in ns}
        reachable=sorted(n for n in known if n==loc or public_route(self,n))
        return dict(visible=sorted(self.visible()),observed_locations={n:sorted(t.places[n]['objects'])
            for n in reachable if n in t.places},reachable=reachable,inspected=sorted(t.inspected))

    def locations(self,item):
        t=self.table
        return [loc for loc,data in sorted(t.places.items()) if data['objects'].get(item,0)>0
            and (loc==t.state.get('location') or public_route(self,loc))]

    def _move(self,destination):
        route=public_route(self,destination)
        if route:return 'enter '+q(route[0])
        # Preserve the inherited known-key acquisition behavior when a public
        # locked edge can be resolved from a publicly held/stored key.
        if route is None and self.table.count('key'):
            return super()._move(destination)
        return None

    def probe_key(self,entry):
        return digest([self.blocker_key21,entry['kind'],entry['entry'],entry.get('destination')])

    def probe_entries(self):
        t=self.table;entries=[];loc=t.state.get('location')
        def add(kind,name,dest,route):
            action=('enter '+q(route[0])) if route else ('inspect '+q(name))
            row=dict(kind=kind,entry=name,destination=dest,route=route,action=action,
                transit_steps=len(route) if kind=='object' else max(0,len(route)-1),
                public_source='current_object' if not route else 'observed_public_route',
                relevant=name in self.needed(),legal=self._usable(action),
                is_transit=bool(route and (kind=='object' or len(route)>1)))
            row['key']=self.probe_key(row);row['attempted']=self.probe_attempts21.get(row['key'],0)>0
            if row['legal'] and not row['attempted']:entries.append(row)
        for name in sorted(self.visible()):
            if name not in t.inspected:add('object',name,loc,[])
        for dest,data in sorted(t.places.items()):
            route=public_route(self,dest)
            if route:
                for name,n in sorted(data['objects'].items()):
                    if n>0 and name not in t.inspected:add('object',name,dest,route)
        for dest in sorted({n for ns in t.links.values() for n in ns}-set(t.places)):
            route=public_route(self,dest)
            if route:add('frontier',dest,dest,route)
        # No semantic ranking. Current public dependency membership, distance,
        # type and exact identifiers are fixed mechanical tie breakers.
        return sorted(entries,key=lambda e:(not e['relevant'],len(e['route']),e['kind'],e['entry'],e['destination']))

    def _new_probe(self,entry,source,grant_id=None):
        self.probe21=dict(id='probe21_'+str(len(self.probe_log21)+1),entry=copy.deepcopy(entry),source=source,
            grant_id=grant_id,start_step=self.step16,actions=[],transit_used=0,probe_used=0,
            blocker=knowledge.blocker(self),path_before=self._known_path(self.blocker20.get('item','')),
            stages=[],status='active',remaining_actions=MAX_PROBE_ACTIONS)

    def _close_probe(self,reason):
        if not self.probe21:return
        p=self.probe21
        p.update(status=reason,end_step=self.step16)
        if reason not in ('normal_exploration_budget','known_execution_available','method_stalled'):
            self.probe_attempts21[p['entry']['key']]=self.probe_attempts21.get(p['entry']['key'],0)+1
        self.probe_log21.append(copy.deepcopy(p))
        if p['grant_id']:self.etbr21.finish(p['grant_id'],reason,self.step16)
        self.probe21=None

    def _probe_action(self):
        probe=self.probe21
        if not probe:return None
        if self.risk16:self._close_probe('public_risk');return None
        if probe['remaining_actions']<=0:self._close_probe('bounded_probe_action_limit');return None
        entry=probe['entry'];loc=self.table.state.get('location')
        if entry['destination']!=loc:
            route=public_route(self,entry['destination'])
            if not route:self._close_probe('public_route_unavailable');return None
            final=entry['kind']=='frontier' and len(route)==1
            if not final and probe['transit_used']>=MAX_TRANSIT_STEPS:
                self._close_probe('transit_step_limit');return None
            action='enter '+q(route[0]);is_transit=not final
        elif entry['kind']=='object' and entry['entry'] in self.visible() and entry['entry'] not in self.table.inspected:
            action='inspect '+q(entry['entry']);is_transit=False
        else:self._close_probe('entry_exhausted_or_already_observed');return None
        if not self._usable(action):self._close_probe('public_condition_reject');return None
        if probe['grant_id']:
            # Extra actions have their own accounting. Never change the original
            # 18-action exploration limit or simulate an unspent normal action.
            self.selection21=dict(probe_id=probe['id'],grant_id=probe['grant_id'],is_transit=is_transit,entry=copy.deepcopy(entry))
            return action
        action=self._probe(action,'single_bounded_public_probe',{'probe_id':probe['id'],'entry':entry['entry']})
        if action:self.selection21=dict(probe_id=probe['id'],grant_id=None,is_transit=is_transit,entry=copy.deepcopy(entry))
        else:self._close_probe('normal_exploration_budget')
        return action

    def exploration_entry(self):
        if self.exploration_spent>=NORMAL_EXPLORATION or self.risk16:return None
        entries=self.probe_entries()
        if not entries:return None
        self._new_probe(entries[0],'engineering_public_entry')
        return self._probe_action()

    def can_request(self):
        return bool(self.exploration_spent<NORMAL_EXPLORATION and not self.risk16
            and self.plan_calls20<MAX_PLANNING_CALLS and self.context_counts20.get(self.planning_context(),0)<1
            and self.probe_entries())

    def accept(self,proposal,prompt=None):
        from .planning import validate
        from .evidence import check
        validate(proposal);evidence=check(self,proposal)
        reason=None if evidence['hypothesis_accept'] else evidence['reason']
        name=proposal['target'] if proposal['type'] in ('INSPECT_OBJECT','EXPLORE_FRONTIER') else proposal['entry']
        possible=[e for e in self.probe_entries() if e['entry']==name]
        if not possible:reason=reason or 'no_untried_bounded_probe_entry'
        if self.probe21:reason=reason or 'pending_probe_conflict'
        if self.exploration_spent>=NORMAL_EXPLORATION:reason=reason or 'normal_exploration_budget'
        if self.risk16:reason=reason or 'public_risk'
        record=dict(proposal=copy.deepcopy(proposal),accepted=reason is None,reason=reason or 'public_probe_hypothesis',
            evidence_check=evidence,step=self.step16,evidence_refs=[copy.deepcopy(self.evidence20[x]) for x in proposal['evidence_ids'] if x in self.evidence20])
        if reason is None:
            self._new_probe(possible[0],'LLM_public_probe');record['probe_id']=self.probe21['id']
        self.acceptance20.append(record);self.last_plan20=copy.deepcopy(record)
        return record

    def _commit(self,trial,action,source):
        selected=copy.deepcopy(trial.selection21)
        if source in ('P3_finish','known_FIFO_execution','public_dependency_execution') and trial.probe21:
            trial._close_probe('known_execution_available')
        normal_before=self.exploration_spent
        result=super()._commit(trial,action,source)
        if selected and selected['grant_id']:
            assert self.exploration_spent==normal_before
        self.audit20['stage21']=dict(selection=selected,etbr_last_check=copy.deepcopy(self.etbr21.last_check),
            normal_exploration=self.exploration_spent,grants=len(self.etbr21.grants),pending_probe=copy.deepcopy(self.probe21))
        if selected and selected['is_transit']:
            self.engineering21.append(dict(step=self.step16+1,event='public_transit_executed',action=action,
                route=selected['entry']['route'],destination=selected['entry']['destination'],grant_id=selected['grant_id']))
        return result

    def choose(self,obs,allow_fallback=False):
        self.table.observe(obs)
        if not self.initial_evidence21:
            self.etbr21.ingest(knowledge.facts(self),None,self.step16,initial=True)
            self.initial_evidence21=True
        self.condition_log,self.decision10,self.selected_meta=[],{},None
        self.probe_candidates20,self.acquisitions20,self.mechanism_decision=[],[],{}
        self.selection21=None;self.active_precondition20=None;self.blocker20={}
        trial=copy.deepcopy(self);action,_=trial.finish('wait')
        if action and trial._usable(action):return self._commit(trial,action,'P3_finish')
        trial=copy.deepcopy(self);action=Budget100Controller.choose(trial,obs,'wait')
        action=trial._bound(action,source='final_FIFO_candidate')
        if trial._reliable_fifo(trial,action):return self._commit(trial,action,'known_FIFO_execution')
        known=copy.deepcopy(self);candidate=known.known_step(parse_action(self.target).target,self.amount)
        if known._usable(candidate):return self._commit(known,candidate,'public_dependency_execution')
        self.blocker20=known.blocker20 or dict(kind='known_execution_blocked',item=parse_action(self.target).target)
        self.blocker20['public_entries']=self.public_entries()
        block=knowledge.blocker(self);self.blocker_key21=blocker_id(block)
        if self.probe21:
            trial=copy.deepcopy(self);candidate=trial._probe_action()
            if candidate:return self._commit(trial,candidate,'ETBR_probe' if trial.probe21['grant_id'] else 'bounded_probe')
            self.probe21,self.probe_log21,self.probe_attempts21,self.etbr21=trial.probe21,trial.probe_log21,trial.probe_attempts21,trial.etbr21
        entries=self.probe_entries()
        if self.exploration_spent>=NORMAL_EXPLORATION or not entries:
            trial=copy.deepcopy(self)
            grant=trial.etbr21.offer(block,entries,step=self.step16,risk=self.risk16,request_available=self.plan_calls20<MAX_PLANNING_CALLS)
            if grant:
                trial._new_probe(grant['entry'],'ETBR',grant['id']);candidate=trial._probe_action()
                if candidate:return self._commit(trial,candidate,'ETBR_probe')
            self.etbr21=trial.etbr21
        # With one candidate there is no useful choice for a model to make.
        if allow_fallback or len(entries)==1:
            trial=copy.deepcopy(self);candidate=trial.exploration_entry()
            if candidate:return self._commit(trial,candidate,'engineering_public_probe')
        self.recovery('BLOCKED' if self.can_request() else 'STALLED','no_admissible_known_action',blocker=copy.deepcopy(self.blocker20))
        return None

    def observe(self,before,action,after):
        selected=copy.deepcopy(self.selection21);active=copy.deepcopy(self.probe21)
        own_before={n:self.ownership(n)['lower_bound'] for n in self.needed()}
        paths={g['id']:self._known_path(g['blocker']['subject']) for g in self.etbr21.grants}
        super().observe(before,action,after)
        new=self.etbr21.ingest(knowledge.facts(self),action,self.step16,initial=not self.in_episode)
        feedback=self.table.state['feedback'];invalid=bool(re.search(r'Cannot |Invalid ',feedback))
        stage_events=[]
        if active and self.probe21 and selected and selected['probe_id']==active['id']:
            p=self.probe21;p['remaining_actions']-=1
            p['actions'].append(dict(step=self.step16,action=action,is_transit=selected['is_transit']))
            p['transit_used' if selected['is_transit'] else 'probe_used']+=1
            if not selected['is_transit'] and not invalid:stage_events.append(dict(stage='PROBE_COMPLETED',step=self.step16))
            if new:stage_events.append(dict(stage='NEW_EVIDENCE_OBTAINED',step=self.step16,evidence_ids=[d['evidence_id'] for d in new]))
            p['stages']+=copy.deepcopy(stage_events)
            if p['grant_id']:
                g=next(g for g in self.etbr21.grants if g['id']==p['grant_id'])
                g['actions']=copy.deepcopy(p['actions']);g['transit_used']=p['transit_used'];g['probe_used']=p['probe_used']
                g['stage_events']+=copy.deepcopy(stage_events);g['knowledge_gains'] += [d['evidence_id'] for d in new]
            if invalid:self._close_probe('native_rejection')
            elif self.risk16:self._close_probe('public_risk')
            elif not selected['is_transit']:self._close_probe('probe_completed')
        # Downstream records are temporal associations with publicly linked
        # obligations, not a multi-step counterfactual causal estimate.
        source=self.audit20.get('source')
        paction=parse_action(action)
        for g in self.etbr21.grants:
            subject=g['blocker']['subject'];entities=set(g['blocker']['public_entities'])
            gains={n:self.ownership(n)['lower_bound']-v for n,v in own_before.items()
                if paction.verb in ('pick up','store','take out','buy') and paction.target==n
                and n in entities and self.ownership(n)['lower_bound']>v}
            if gains:
                g['material_gains'].append(dict(step=self.step16,action=action,gains=gains))
            resolved=(not paths[g['id']] and self._known_path(subject))
            ground_needed=g['blocker'].get('requires_ground')
            satisfied=bool((self.table.state.get('ground') or {}).get(subject,0)) if ground_needed else self.ownership(subject)['lower_bound']>=g['blocker'].get('required_amount',1)
            if (resolved or satisfied) and not g['precondition_resolved']:
                g['precondition_resolved']=True
                g['stage_events'].append(dict(stage='PRECONDITION_RESOLVED',step=self.step16,kind='actual_presence' if satisfied else 'public_executable_path'))
            if g['precondition_resolved'] and source in ('known_FIFO_execution','public_dependency_execution','P3_finish') and paction.target in entities and not invalid:
                if not g['parent_task_resumed']:
                    g['parent_task_resumed']=True;g['stage_events'].append(dict(stage='PARENT_TASK_RESUMED',step=self.step16,action=action))
            if 'successfully crafted' in feedback and paction.target in entities:
                g['task_progress']=True;g['stage_events'].append(dict(stage='TASK_PROGRESS',step=self.step16,action=action))
        self.transition21=dict(new_evidence=new,selection=selected,stages=stage_events,invalid=invalid,
            pending_probe=copy.deepcopy(self.probe21),latest_probe=copy.deepcopy(self.probe_log21[-1:]),
            normal_exploration=self.exploration_spent,etbr=copy.deepcopy(self.etbr21.to_dict()))
        self.outcome20['stage21']=copy.deepcopy(self.transition21)
        self.selection21=None

    def to_dict(self):
        data=super().to_dict();data['etbr21']=self.etbr21.to_dict();return data

    @classmethod
    def from_dict(cls,data):
        obj=cls();obj.__dict__.update(BaselineController.from_dict(data).__dict__)
        obj.etbr21=Recovery.from_dict(data.get('etbr21',{}));obj.intent20=obj.suspended20=None
        return obj

