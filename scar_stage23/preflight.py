"""Exact prompt/noninterference and rejection-guard tests, no network."""
import contextlib
import copy
import io
import tempfile
from .common import *
from .prepare import load_agent_state
from .reset import ResetGate,ResetArbitration,attach


def main():
    from scar_stage22b.common import forbid_network,internal
    forbid_network()
    from scar_stage22.integration import make_agent
    from scar.io import digest
    from scar_stage18.arbitration import choose as original_choose
    original=rows(SOURCE/'trajectory.jsonl.gz');requests=rows(SOURCE/'requests.jsonl.gz')
    states=rows(ROOT/'results/stage22b/agent_audit/Stage18-Fixed.jsonl.gz')
    class Saved:
        n=0;calls=0
        def generate(self,user_prompt,system_prompt=None,**kwargs):
            q=requests[self.n-1]
            assert q['messages']==[dict(role='system',content=system_prompt),dict(role='user',content=user_prompt)],('prompt',self.n)
            self.calls+=1
            return dict(response=q['raw_response']['choices'][0]['message']['content'],
                num_input_tokens=q['usage']['prompt_tokens'],num_output_tokens=q['usage']['completion_tokens'])
    evidence=[]
    with tempfile.TemporaryDirectory(prefix='scar23-preflight-') as temp:
        # Gate disabled: inherited code, every original action and every full
        # decision digest remains identical over the complete source episode.
        provider=Saved()
        with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('Stage18-Fixed','mark',provider,Path(temp)/'disabled')
        agent.initialize_official(read(SOURCE/'initial_public.json')['observation'])
        attach(agent,'Stage18-Reset');off=ResetGate('Stage18-Origin',1)
        for r in original:
            provider.n=r['step']
            with off.enabled(),contextlib.redirect_stdout(io.StringIO()):action,*_=agent.act(r['observation'])
            assert action==r['action'] and digest(agent.decision)==digest(r['decision'])
            agent.observe_transition(r['observation'],action,r['feedback'])
        # Every fork retains exactly the original first input. Gate activation
        # cannot mutate memory/facts/controller before the model call.
        for start in CASES:
            for variant in VARIANTS:
                provider=Saved();provider.n=start
                with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('Stage18-Fixed','mark',provider,Path(temp)/'fork')
                load_agent_state(agent,states[start-1]['internal_before']);attach(agent,variant)
                gate=ResetGate(variant,start,original[:start-1])
                before=internal(agent,'Stage18-Fixed')
                state=gate.before(start,agent.controller,original[start-1]['observation'])
                assert internal(agent,'Stage18-Fixed')==before
                with gate.enabled(),contextlib.redirect_stdout(io.StringIO()):action,*_=agent.act(original[start-1]['observation'])
                assert before['explicit_goal_field']==agent.controller.target
                evidence.append(dict(case=case_id(start),variant=variant,reset=state,first_action=action,
                    raw_proposal=agent.decision['proposed_action'],original_action=original[start-1]['action'],
                    exact_first_prompt=True,controller_goal_not_deleted=True))
        # REJECT proposals remain corrected even under an oracle release.
        for n in [65,67]:
            provider=Saved();provider.n=n
            with contextlib.redirect_stdout(io.StringIO()):agent=make_agent('Stage18-Fixed','mark',provider,Path(temp)/'reject')
            load_agent_state(agent,states[n-1]['internal_before']);attach(agent,'Oracle-Reset')
            gate=ResetGate('Oracle-Reset',n,original[:n-1]);gate.before(n,agent.controller,original[n-1]['observation'])
            with gate.enabled(),contextlib.redirect_stdout(io.StringIO()):action,*_=agent.act(original[n-1]['observation'])
            assert action==original[n-1]['action']=='enter hall'
            assert agent.decision['stage18']['assessments']['llm']['status']=='REJECT'
        # Exhaustive arbitration status combinations, with reset off/on. Only
        # the unresolved default branch may change; no extra action invented.
        count=0
        c=agent.controller
        for base in ['REJECT','UNKNOWN','SUPPORTED']:
            for candidate in ['REJECT','UNKNOWN','SUPPORTED']:
                checks=dict(llm=dict(status=base,known_goal_progress=False),bounded_controller=dict(status=candidate))
                old=original_choose(c,'talk to someone','wait',checks)
                with gate.enabled():new=ResetArbitration.choose(c,'talk to someone','wait',checks)
                assert new[0] in {old[0],'talk to someone'}
                if base=='REJECT':assert new==old
                count+=1
    write(RESULTS/'preflight.json',dict(passed=True,disabled_exact_actions_and_decisions=300,
        first_prompt_comparisons=30,full_hands_rejections_preserved=2,status_combination_checks=count,
        fork_results=evidence,new_api_calls=0))
    print(json.dumps(dict(passed=True,disabled_actions=300,exact_fork_prompts=30,api_calls=0)),flush=True)


if __name__=='__main__':main()
