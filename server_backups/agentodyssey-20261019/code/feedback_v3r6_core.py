"""Constrain heuristic veto authority; preserve observed feasibility checks.

Resource recurrence still pauses automatic continuation. A fresh actor decision
may override its warning; lack of parent progress is not physical impossibility.
Emergency effects use the separately tested v3r5 progress scope.
"""
import copy
try:
    from .feedback_v3r5_core import Ledger as Previous,NO_RESOURCE_PROGRESS
except ImportError:
    from feedback_v3r5_core import Ledger as Previous,NO_RESOURCE_PROGRESS

class Ledger(Previous):
    def __init__(self):
        super().__init__();self.authority_audit=[]

    def gate(self,seq,goal,source):
        c,v=super().gate(seq,goal,source);demoted=[];kept=[]
        for b in c['blockers']:
            if b['kind']=='same_failed_action_context' and b['detail'].get('reason')==[NO_RESOURCE_PROGRESS]:demoted.append(b)
            else:kept.append(b)
        c['blockers']=kept
        if demoted:
            c['warnings'].append({'kind':'task_no_progress_requires_reassessment','action':seq[0],
                'evidence_step':demoted[-1]['detail']['step'],
                'meaning':'Recurring task state: expected benefit needs fresh reasoning. This is not evidence that the action cannot execute.'})
            self.authority_audit.append({'step':self.step,'action':seq[0],'source':source,'event':'heuristic_veto_demoted','original':demoted,'remaining_blockers':copy.deepcopy(kept)})
        if self.control_checks:self.control_checks[-1].update(blockers=copy.deepcopy(kept),demoted_progress_rules=copy.deepcopy(demoted))
        return c,v

    def _select_plan(self,seq,goal,source):
        if source.startswith('local_'):
            check,_=self.gate(seq,goal,source)
            if any(w['kind']=='task_no_progress_requires_reassessment' for w in check['warnings']):
                self.authority_audit.append({'step':self.step,'action':seq[0],'source':source,'event':'automatic_continuation_paused','meaning':'Fresh actor decision required; not an environment prohibition.'})
                return None
        return super()._select_plan(seq,goal,source)

    def dispatch(self,candidates,goal):
        return super().dispatch(candidates,goal)

    def local_action(self,goal):
        result=super().local_action(goal)
        if result and any(w['kind']=='task_no_progress_requires_reassessment' for w in result[1]['warnings']):
            self.authority_audit.append({'step':self.step,'action':result[0],'source':result[2]['source'],'event':'automatic_continuation_paused'})
            return None
        return result

    def authority_packet(self):
        return {'policy':'Observed constraints can reject actions. Parent-task recurrence is advisory to fresh actor choices and pauses automatic continuation.',
                'recent':[{'step':x['step'],'action':x['action'],'event':x['event']} for x in self.authority_audit[-3:]]}

    def to_dict(self):
        p=super().to_dict();p['v3r6_authority_audit']=self.authority_audit;return p
