import json
from scar_public.continuation import ContinuationAgent
from scar_public.continuation_control import GenericContinuationAgent
from scar_public.test_continuation import obs


def test_generic_control_changes_only_repair_query_evidence_exposure():
    class LLM:
        step=0
        def __init__(self):self.prompts=[]
        def generate(self,user,system):
            self.prompts.append((system,user))
            repair='\nContinuation repair packet:\n' in user or '\nReconsideration options:\n' in user
            response=dict(action='enter yard' if repair else 'enter vault',reasoning='Seek route',
                expected='Observe another exit',frame=dict(goal_quote='Visit the vault.',
                method='Find a route',assessment='Pending',expected='Observe route'))
            return dict(response=json.dumps(response),num_input_tokens=1,num_output_tokens=1)
    full=ContinuationAgent(LLM(),'Return JSON.')
    generic=GenericContinuationAgent(LLM(),'Return JSON.')
    initial=obs(feedback='guide says: Visit the vault.')
    failure=obs(feedback='Cannot enter vault, the door is locked.')
    for step,text in enumerate((initial,failure)):
        for agent in (full,generic):agent.llm.step=step
        left=full.act(dict(text=text));right=generic.act(dict(text=text))
        assert left[0]==right[0]
        assert full.notebook.state()==generic.notebook.state()
    assert len(full.llm.prompts)==len(generic.llm.prompts)==3
    assert full.llm.prompts[:2]==generic.llm.prompts[:2]
    assert '\nContinuation repair packet:\n' in full.llm.prompts[-1][1]
    assert '\nReconsideration options:\n' in generic.llm.prompts[-1][1]
    assert 'REPEATED_OBSERVED_FAILURE' not in generic.llm.prompts[-1][1]
    assert 'Cannot enter vault' in generic.llm.prompts[-1][1]  # Original ledger retained.
