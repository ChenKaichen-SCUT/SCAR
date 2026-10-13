"""On-demand subgoal requests; deterministic execution makes no model call."""
import copy
import json
from functools import lru_cache
from pathlib import Path
from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from scar_stage16.agent import BaselineAgent
from scar_stage16.knowledge import PublicFacts16
from scar_stage16 import config as baseline
from scar.agents.scar.repair import valid_syntax
from scar.io import atomic_json
from .controller import Controller20
from .execution_context import render


class Agent20(BaselineAgent):
    def __init__(self, id, name, cfg=None):
        super().__init__(id, name, cfg)
        self.controller = Controller20()
        self.memory_paths = ['memory.json', 'stage20.json']

    @property
    def public_state(self):
        from scar_stage16.state import PublicRuleState
        return PublicRuleState(self.controller.legacy_copy())

    def _act(self, obs):
        from .planning import SYSTEM,FIELDS,validate
        from scar.providers.deepseek import ModelResponseError
        from .run_errors import MethodStalled
        before=self.controller.to_dict();action=self.controller.choose(obs)
        plans=[];tin=tout=0;responses=[];self.decision={}
        # At most two logical plans for this decision; each has the unchanged
        # three paid-attempt protocol. Context and episode caps also apply.
        for _ in range(2):
            if action:break
            if not self.controller.can_request():
                action=self.controller.choose(obs,allow_fallback=True);break
            trigger=copy.deepcopy(self.controller.blocker20)
            self.controller.start_request()
            prompt,summary=render(self.controller,obs,self.short_term_memory)
            self.last_user_prompt=prompt
            entry=dict(trigger=trigger,evidence_snapshot=copy.deepcopy(summary),
                context=self.controller.planning_context(),context_attempt=self.controller.context_counts20[self.controller.planning_context()])
            try:
                result=self.cfg.scar_provider.generate(user_prompt=prompt,system_prompt=SYSTEM,
                    required=FIELDS,phase='subgoal',max_tokens=baseline.MAX_TOKENS,validator=validate)
                proposal=result['parsed'];acceptance=self.controller.accept(proposal,prompt)
                tin+=result['num_input_tokens'];tout+=result['num_output_tokens'];responses.append(result['response'])
                entry.update(status='ok',proposal=proposal,acceptance=copy.deepcopy(acceptance))
            except ModelResponseError:
                self.controller.planning_failed('three_audited_interface_attempts_failed')
                entry.update(status='interface_unavailable',proposal=None,acceptance=None)
            plans.append(entry)
            action=self.controller.choose(obs)
            if not action:action=self.controller.choose(obs,allow_fallback=True)
        if action and not valid_syntax(action,self.available_actions):
            # Roll back the entire unexecuted choice; preserve paid-call history.
            post=self.controller;self.controller=Controller20.from_dict(before)
            for field in ('plan_calls20','request_contexts20','context_counts20','acceptance20','evidence20','request_evidence20'):
                setattr(self.controller,field,copy.deepcopy(getattr(post,field)))
            self.controller.recovery('STALLED','invalid_syntax_transaction_rollback',rejected=action);action=None
        self.decision=dict(llm_called=bool(plans),planning_calls=plans,executed_action=action,
            controller_before=before,stage20=copy.deepcopy(self.controller.audit20),
            active_subgoal=copy.deepcopy(self.controller.intent20),recovery=copy.deepcopy(self.controller.recovery20),
            variant='SCAR20',no_action_proposal_interface=True,extra_repair_call=False)
        if not action:
            if self.controller.intent20:self.controller.close_intent('censored','method_stalled')
            if self.controller.suspended20:
                self.controller.intent20=self.controller.suspended20;self.controller.suspended20=None
                self.controller.close_intent('blocked','method_stalled')
            self.controller.recovery('STALLED','no_admissible_public_progress_after_bounded_recovery')
            raise MethodStalled('No admissible public action; finite recovery exhausted or unavailable')
        self.memorize(f"{obs['text']}\nExecuted action: {action}\nSource: {self.controller.audit20.get('source')}")
        self.events+=self.controller.events;self.controller.events.clear()
        return action,tin,tout,'\n'.join(responses)

    def save_memory(self, directory):
        ShortTermMemoryAgent.save_memory(self, directory)
        atomic_json(Path(directory)/'stage20.json', dict(schema_version=1, method='SCAR20',
            controller=self.controller.to_dict(), facts=self.facts.to_dict(),
            system_prompt=self.cfg.system_prompt, action_prompt=self.cfg.action_prompt,
            model=baseline.MODEL, stm_size=baseline.STM_SIZE))

    def load_memory(self, directory):
        data = json.loads((Path(directory)/'stage20.json').read_text())
        assert data['schema_version'] == 1 and data['method'] == 'SCAR20'
        assert data['model'] == baseline.MODEL and data['stm_size'] == baseline.STM_SIZE
        assert data['action_prompt'] == self.cfg.action_prompt
        ShortTermMemoryAgent.load_memory(self, directory)
        assert self.short_term_memory_size == baseline.STM_SIZE
        self.controller = Controller20.from_dict(data['controller'])
        self.facts = PublicFacts16.from_dict(data['facts'])
        self.cfg.system_prompt = data['system_prompt']


@lru_cache(None)
def agent_class(base):
    return type('SCAR20__'+base.__name__, (Agent20, base), {'__module__': base.__module__})


def make_agent(provider, *, game, memory_dir='memory_stage20'):
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    cfg = DeepSeekMemoryConfig(llm_name=baseline.MODEL, llm_provider='deepseek',
        embed_name=baseline.EMBEDDING_MODEL, max_new_tokens=baseline.MAX_TOKENS,
        temperature=baseline.TEMPERATURE, short_term_memory_size=baseline.STM_SIZE,
        torch_seed=42, full_mem_path=str(memory_dir))
    cfg.scar_provider = provider
    return agent_class(dynamic_load_game_class(game, 'agent', 'Agent'))('agent_adam_davis', 'adam_davis', cfg)


def make_method(method, game, provider, objective, target, history, folder):
    assert method == 'SCAR20'
    agent = make_agent(provider, game=game, memory_dir=folder)
    agent.initialize_episode(history, 'craft 1 '+target, objective)
    return agent


def decision_state(agent, method):
    assert method == 'SCAR20'
    return dict(decision=copy.deepcopy(agent.decision), controller=agent.controller.to_dict(),
                memory=list(agent.short_term_memory))
