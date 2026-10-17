import json
import pytest
from scar_public.continuation import ContinuationAgent
from scar_public.experiments.scheduled_continuation import ScheduledContinuationAgent, fixed_schedule
from scar_public.test_continuation import obs


def test_grid_uses_only_quota_and_budget():
    assert fixed_schedule(0)==[]
    assert fixed_schedule(3)==[75,150,225]
    assert fixed_schedule(1,20)==[10]
    with pytest.raises(ValueError):fixed_schedule(301)


def test_scheduled_trigger_has_no_failure_requirement_and_protects_combat():
    class LLM:step=0
    agent=ScheduledContinuationAgent(LLM(),'JSON',1,20)
    agent.continuation.observe(obs(),9)
    assert agent.repair_trigger('enter vault','task') is None
    agent.continuation.observe(obs(),10)
    assert agent.repair_trigger('attack monster','task') is None
    trigger=agent.repair_trigger('enter vault','task')
    assert trigger['kind']=='PRESCHEDULED_RECONSIDERATION'
    assert trigger['witnesses']==[]
    agent.repair_queries_used=1
    assert agent.repair_trigger('enter vault','task') is None


def test_zero_quota_never_activates_even_on_failure():
    class LLM:step=0
    agent=ScheduledContinuationAgent(LLM(),'JSON',0)
    agent.continuation.observe(obs(),0)
    agent.continuation.commit('enter vault','task')
    agent.continuation.observe(obs(feedback='Cannot enter vault, the door is locked.'),1)
    assert agent.continuation.assess('enter vault','task')
    assert agent.repair_trigger('enter vault','task') is None


def test_scheduled_missing_anchor_delays_call_without_spending_quota():
    class LLM:step=1
    agent=ScheduledContinuationAgent(LLM(),'JSON',1,2)
    text=obs();agent.continuation.observe(text,1)
    agent.notebook.model.observe(text)
    proposal=dict(action='enter vault',reasoning='Continue')
    def forbidden(_):raise AssertionError('No anchor: no call')
    result=agent.finalize_decision(proposal,dict(text=text),1,'prompt',forbidden)
    assert agent.repair_queries_used==0
    assert result['continuation']['reason']=='NO_PUBLIC_TASK_OR_AVAILABLE_OPTION'


def test_default_hook_keeps_original_evidence_decision():
    class LLM:step=0
    agent=ContinuationAgent(LLM(),'JSON')
    agent.continuation.observe(obs(),0)
    agent.continuation.commit('enter vault','task')
    agent.continuation.observe(obs(feedback='Cannot enter vault, the door is locked.'),1)
    assert agent.repair_trigger('enter vault','task')==agent.continuation.assess('enter vault','task')


def test_scheduled_and_compact_use_same_query_and_failure_gate_at_matching_time():
    from scar_public.continuation_control import GenericContinuationAgent
    class LLM:
        step=0
        def __init__(self):self.prompts=[]
        def generate(self,user,system):
            self.prompts.append(user)
            response=dict(action='enter vault',reasoning='Continue',
                frame=dict(goal_quote='Visit the vault.',method='Travel',assessment='Pending',expected='Arrive'))
            if 'Reconsideration options:' in user:
                response['alternatives']=[dict(action='enter yard',reasoning='Try route',expected='See route')]
            return dict(response=json.dumps(response),num_input_tokens=1,num_output_tokens=1)
    compact=GenericContinuationAgent(LLM(),'JSON')
    scheduled=ScheduledContinuationAgent(LLM(),'JSON',1,2)
    for step,text in enumerate((obs(feedback='guide says: Visit the vault.'),
                                obs(feedback='Cannot enter vault, the door is locked.'))):
        for agent in (compact,scheduled):
            agent.llm.step=step;agent.act(dict(text=text))
    assert compact.llm.prompts==scheduled.llm.prompts
    event=scheduled.continuation_events[-1]
    assert event['executed']=='enter yard'
    assert event['rejected'][0]['reasons']==['REPEATED_OBSERVED_FAILURE']
    assert scheduled.repair_queries_used==1
