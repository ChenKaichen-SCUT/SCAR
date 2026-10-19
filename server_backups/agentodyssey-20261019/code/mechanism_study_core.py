"""Explicit single-component ablations of the frozen v3 implementation."""
import copy,json,os
try:
    from .feedback_v3_core import Ledger as V3Ledger
except ImportError:
    from feedback_v3_core import Ledger as V3Ledger

COMPONENTS={'joint_checks','dependency_execution','hard_repeat','hypothesis'}
VARIANTS={'full_reference':set(),'no_checks':{'joint_checks'},'no_execution':{'dependency_execution'},'no_repeat':{'hard_repeat'},'no_hypothesis':{'hypothesis'}}
JOINT={'quantity_deficit','task_parameter_mismatch','station_not_currently_observed','observed_hand_capacity','observed_container_capacity','already_satisfied_dependency'}
REPEAT={'repeated_context_action','inspection_has_no_new_question'}

class StudyLedger(V3Ledger):
    def __init__(self,disabled=None):
        super().__init__()
        if disabled is None:
            variant=os.environ.get('AO_STUDY_VARIANT','full_reference')
            disabled=set(json.loads(os.environ.get('AO_DISABLED_COMPONENTS','[]'))) if variant=='v4_selected' else VARIANTS[variant]
        self.disabled=set(disabled);assert self.disabled<=COMPONENTS
    def preparation(self):
        return None if 'dependency_execution' in self.disabled else super().preparation()
    def dispatch(self,candidates,goal_id):
        if 'dependency_execution' in self.disabled:self.queue=[]
        result=super().dispatch(candidates,goal_id)
        if 'dependency_execution' in self.disabled:self.queue=[]
        return result
    def action_check(self,action,goal_id=None,schemas=None):
        check=super().action_check(action,goal_id,schemas)
        disabled=(JOINT if 'joint_checks' in self.disabled else set())|(REPEAT if 'hard_repeat' in self.disabled else set())
        removed=[b for b in check['blockers'] if b['kind'] in disabled]
        check['blockers']=[b for b in check['blockers'] if b['kind'] not in disabled]
        check['warnings'] += [dict(b,intervention='advisory_only_component_disabled') for b in removed]
        return check
    def apply_review(self,r):
        if 'hypothesis' in self.disabled and isinstance(r,dict):r={k:v for k,v in r.items() if k!='hypotheses'}
        return super().apply_review(r)
    def choose(self,action,reasoning,goal_id=None,test_id=None,check=None):
        super().choose(action,reasoning,goal_id,None if 'hypothesis' in self.disabled else test_id,check)
    def packet(self):
        p=super().packet()
        if 'hypothesis' in self.disabled:
            p.pop('hypotheses',None);p['recent_outcomes']=copy.deepcopy(p['recent_outcomes'])
            for o in p['recent_outcomes']:o.pop('hypothesis_test',None)
        return p
