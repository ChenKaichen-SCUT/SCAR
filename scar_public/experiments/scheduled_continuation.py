"""Count-matched timing control, not a proposed new SCAR policy.

Only the scalar number of compact repair queries is used to set a grid. No
reference actions, observations, rewards, trigger times or hidden state enter
this agent. This is a retrospective resource-matched control: the reference
count is not known online. Total tokens and terminal-truncated calls may differ.
"""
from scar_public.continuation import PROTECTED, threatened
from scar_public.continuation_control import GenericContinuationAgent


def fixed_schedule(quota, horizon=300):
    if not 0 <= quota <= horizon:
        raise ValueError('Invalid repair quota')
    return [(i+1)*horizon//(quota+1) for i in range(quota)]


class ScheduledContinuationAgent(GenericContinuationAgent):
    def __init__(self, llm, system_prompt, quota, horizon=300):
        super().__init__(llm, system_prompt, 'repair')
        self.schedule = fixed_schedule(quota, horizon)
        self.repair_queries_used = 0

    def repair_trigger(self, action, task):
        evidence = self.continuation
        due = sum(step <= evidence.step for step in self.schedule)
        if self.repair_queries_used >= due:
            return None
        if action.startswith(PROTECTED) or threatened(evidence.observation or ''):
            return None
        context = evidence.context(action, task)
        if context is None:
            return None
        return dict(kind='PRESCHEDULED_RECONSIDERATION', action=action,
                    context=context, witnesses=[], expiry=evidence.step,
                    qualification='Clock schedule, independent of failure evidence')

    def finalize_decision(self, executed, obs, step, prompt, query):
        result = super().finalize_decision(executed, obs, step, prompt, query)
        if 'proposal' in result['continuation']:
            self.repair_queries_used += 1
        result['continuation']['scheduled_budget'] = dict(
            quota=len(self.schedule), used=self.repair_queries_used,
            due=sum(s <= step for s in self.schedule))
        return result
