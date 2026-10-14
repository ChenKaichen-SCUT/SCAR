"""Bounded public task history; no recipe binding or inferred prerequisites."""
import copy
import re
from agents.agc.state import extract

def rejected(obs):return bool(extract(obs)['failed'] or re.search(r'^Failed to\b',extract(obs)['feedback'],re.I))

class TaskState:
    def __init__(self):self.events=[]
    def to_dict(self):return dict(events=copy.deepcopy(self.events))
    @classmethod
    def from_dict(cls,d):
        obj=cls();obj.events=copy.deepcopy(d['events']);return obj
    def observe(self,before,action,after,goal,control_after):
        b,a=extract(before),extract(after)
        changes={k:dict(before=b[k],after=a[k]) for k in ['location','hands','equipment','observed_container_contents','ground','npcs'] if b[k]!=a[k]}
        g=control_after.get('goal') or {}
        self.events=(self.events+[dict(step=int(after['step']),goal=goal,action=action,rejected=rejected(after),
            public_feedback=a['feedback'],changes=changes,controller_goal_status=g.get('status'),
            controller_completed_goal=g.get('goal_description') if g.get('status')=='COMPLETED' else None)])[-32:]
    def summary(self,obs,goal,candidate=None):
        s=extract(obs);proposed=candidate.get('goal_description') if isinstance(candidate,dict) else None
        action=candidate.get('action') if isinstance(candidate,dict) else None;goals={g for g in [goal,proposed] if g}
        related=[e for e in self.events if e['goal'] in goals or (action and e['action']==action)][-8:]
        return dict(current_goal=goal,proposed_goal=proposed,
            public_current_state={k:s[k] for k in ['location','hands','equipment','observed_container_contents','ground','npcs','neighbors']},
            recent_task_events=related,known_failed_actions=[e for e in related if e['rejected']],
            controller_reported_completed_conditions=[e for e in related if e['controller_completed_goal']],
            last_environment_change=self.events[-1]['changes'] if self.events else {},
            epistemic_boundary='Only observed public fields and at most eight matching task/action events from a 32-transition buffer. '
            'Null means unknown, not empty. Accepted actions and controller completion labels do not prove conditions remain satisfied. '
            'No recipe is inferred to be necessary for an acquisition goal. No hidden quantities, routes or action constraints are supplied.')
