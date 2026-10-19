"""Evaluation repairs only: reject malformed hypothesis arrays; record screen stop.

The frozen agent/ledger files remain untouched. Normal actions, prompts, checks,
and replanning are unchanged. No benchmark entities or hidden state are read.
"""
import json,os
from pathlib import Path
from agents.feedback_v5_core import Ledger,ScreenStopped

def audit(s,event,**detail):
    path=Path(os.environ['AO_RUNTIME_AUDIT']);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:f.write(json.dumps({'event':event,'step':s.step,**detail})+'\n')

original_review=Ledger.apply_review
def validated_review(self,review):
    if isinstance(review,dict) and isinstance(review.get('hypotheses'),list):
        valid=[]
        for h in review['hypotheses']:
            if not isinstance(h,dict) or not isinstance(h.get('preconditions',[]),list) or not isinstance(h.get('expected',[]),list):
                audit(self,'malformed_hypothesis_ignored',hypothesis=h)
                continue
            valid.append(h)
        review={**review,'hypotheses':valid}
    return original_review(self,review)

original_replan=Ledger.request_replan_if_needed
def full_horizon_replan(self):
    try:return original_replan(self)
    except ScreenStopped as error:
        if 'stagnation_after_one_replan' not in str(error):raise
        audit(self,'screen_stop_recorded_without_termination',replan_at=self.replan_at)
        return False

Ledger.apply_review=validated_review
Ledger.request_replan_if_needed=full_horizon_replan
