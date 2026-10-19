"""Full-history ReAct with bounded, observation-grounded feedback control.
Inspired by Sentry/WorldCoder; not a reproduction or a novelty claim.
"""
from __future__ import annotations
import json
import os
from functools import lru_cache
from pathlib import Path
from agents.long_context_agent import LongContextAgent
from agents.feedback_control_core import ControlState, schema_error
from providers.deepseek_adapter import DeepSeekLanguageModel

REVIEW_SYSTEM = '''You are an observation-grounded controller for an interactive agent.
You receive only its declared action schema and past/current textual observations, not hidden state or rewards.
Audit what the agent has learned and whether its previous expected effect actually occurred.
Distinguish direct observation, inference, intention, and confirmed action outcome. Ownership is not the same as seeing an item.
Learn conditional lessons from feedback. A local failure does not prove a universal rule. Keep hypotheses tentative;
revise or retire old lessons when NEW observations contradict them. Do not invent recipes, routes, objects or tool capabilities.
Check whether the executable action can express the intended plan: changing reasoning without changing an effective action is not progress.
Repeated actions can be necessary (combat, resource accumulation, waiting for a known change). A repetition alert is a candidate, not proof of failure.
Judge progress against a concrete near-term subgoal using observations. Moving somewhere or merely avoiding an error is not sufficient proof of task progress.
Use the action interface and observations as given. Do not issue multi-action sequences as one command.
Each evidential quote must be an exact contiguous substring of an observation and reference its observation step.
Return JSON only, with the following schema:
{
 "diagnosis":"brief causal hypothesis and uncertainty; say none if intervention is unnecessary",
 "evidence":[{"step":1,"quote":"exact observed text, at least 12 characters"}],
 "previous_effect_assessment":"confirmed / contradicted / unknown, with reason; do not claim causality",
 "goal":"current task objective supported by observations",
 "subgoal":"one feasible next subgoal or an information-gathering step",
 "expected_change":"observable evidence that would indicate the subgoal is advancing or completed",
 "horizon_steps":6,
 "hypotheses":"uncertain assumptions that must not be treated as facts",
 "rules":[{"id":"stable descriptive id, reuse existing ids when revising",
   "condition":"scope and applicability conditions",
   "lesson":"what evidence implies for action choice",
   "status":"tentative|supported|retired", "evidence":[{"step":1,"quote":"exact observation text"}]}],
 "applicable_rules":[{"id":"existing or newly updated rule id", "applicability":"true|false|unknown",
   "evidence":[{"step":1,"quote":"exact CURRENT observation text"}]}]
}
Use at most 3 rule updates, at most 3 active lessons, and concise text. Empty rules are valid.
Supported means your evidence-based judgment, not a formal guarantee. If recovery was not observed, never store a successful-repair claim.
'''

CONTROL_INSTRUCTION = '''
Feedback-control packet (advisory, derived only from observed experience):
{packet}
Choose one executable action that advances a grounded subgoal. Check known action conditions against the CURRENT observation.
Preserve uncertainty: an old denial may cease to apply after the relevant state changes. A tentative lesson is not a prohibition.
Follow observed tool semantics rather than a narrative reinterpretation. If a tool cannot express the intended change, choose a different executable subgoal.
Do not infer that an attempted action succeeded. Do not repeat a failed or uninformative action unless there is a concrete reason to expect a different outcome now.
Return the original reasoning/action JSON format, with a few sentences only. State what observable change you expect.
'''

class FeedbackControlAgent(LongContextAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.control = ControlState()
        self.schemas = [(a.verb, list(a.params)) for a in self.available_actions]
        self.controller_llm = DeepSeekLanguageModel(
            llm_name=self.cfg.llm_name, max_new_tokens=2048,
            temperature=0.0, presence_penalty=0.0)
        base = os.environ['AO_API_BASE_URL']
        assert base.endswith('/v1')
        self.controller_llm.client.base_url = base[:-3]+'__controller/v1'
        self.audit_path = Path(os.environ['AO_CONTROL_AUDIT'])
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event):
        with self.audit_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False)+'\n')

    def _act(self, obs):
        text = obs['text']  # No access to valid-action oracle, environment state, or reward.
        self.control.advance(text)
        input_tokens = output_tokens = 0
        trigger = self.control.trigger()
        if trigger:
            request = self.control.review_input(text, trigger, self.schemas)
            result = self.controller_llm.generate(
                user_prompt=json.dumps(request, ensure_ascii=False), system_prompt=REVIEW_SYSTEM)
            input_tokens += result['num_input_tokens']; output_tokens += result['num_output_tokens']
            parsed = self.cfg.json_parser(result['response'])
            self.control.apply_review(parsed, trigger)
            self.emit({'step':self.control.step, 'event':'controller', 'trigger':trigger,
                       'response':result['response'], 'accepted':self.control.audit[-1]})

        user_prompt = self.construct_user_prompt_long_context(self.memory.get_all_memory(), text)
        packet = self.control.actor_packet(text)
        user_prompt += CONTROL_INSTRUCTION.format(packet=json.dumps(packet, ensure_ascii=False))
        result = self.llm.generate(user_prompt=user_prompt, system_prompt=self.cfg.system_prompt)
        input_tokens += result['num_input_tokens']; output_tokens += result['num_output_tokens']
        parsed = self.cfg.response_parser(result['response'])
        action = parsed['action']
        violation = schema_error(action, self.schemas)
        repeat = self.control.repeated_denial(action, text)
        attempts = [result['response']]
        # One bounded repair, never best-of-N sampling or outcome-selected restart.
        if (violation or repeat) and self.control.repairs < 32:
            self.control.repairs += 1
            repair = {'proposed_action':action, 'schema_error':violation, 'repeat_warning':repeat,
                      'instruction':'Correct the syntax or choose an observation-grounded alternative. If state/time changed enough to justify repeating a previously denied action, explain the evidence. Return reasoning/action JSON only.'}
            retry = self.llm.generate(user_prompt=user_prompt+'\nAction check:\n'+json.dumps(repair, ensure_ascii=False), system_prompt=self.cfg.system_prompt)
            input_tokens += retry['num_input_tokens']; output_tokens += retry['num_output_tokens']
            result = retry
            parsed = self.cfg.response_parser(retry['response'])
            action = parsed['action']
            attempts.append(retry['response'])
            self.emit({'step':self.control.step,'event':'repair','check':repair,
                       'attempts':attempts,'executed_action':action})
        # Preserve the full observed history. Controller hypotheses stay outside
        # the raw observation history, and only the chosen action is stored here.
        self.memorize(text+'\n'+self.cfg.format_response(parsed))
        self.control.choose(text, action, parsed['reasoning'])
        self.emit({'step':self.control.step,'event':'decision','action':action,
                   'response':result['response'],'attempt_count':len(attempts),
                   'reviews_so_far':self.control.reviews,'repairs_so_far':self.control.repairs,
                   'packet':packet})
        return action, input_tokens, output_tokens, result['response']

    def save_memory(self, full_memory_dir):
        super().save_memory(full_memory_dir)
        path = Path(full_memory_dir)/'feedback_control.json'
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.control.to_dict(),ensure_ascii=False),encoding='utf-8')
        tmp.replace(path)

@lru_cache(maxsize=None)
def create_feedback_control_agent(Agent):
    return type('FeedbackControlAgent__'+Agent.__module__+'.'+Agent.__name__,
                (FeedbackControlAgent,Agent), {'__module__':Agent.__module__, '__agent__':Agent})
