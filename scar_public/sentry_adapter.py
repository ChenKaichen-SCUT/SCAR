"""Integration of pinned AUTHOR Sentry code, with all model calls audited.

Only public action/observation cycles enter Sentry. No reward or engine state.
Uses the same prompt-only SCAR actor; the playbook starts empty in every game.
"""
import json

from scar.io import append_jsonl


SENTRY_REVISION = '1d91bca14fa6a4e17908856cc787eb8e8354395f'


class AuditedJudge:
    def __init__(self, provider):
        self.provider = provider
        self.model = provider.model

    def __call__(self, prompt, **options):
        result = self.provider.request([
            {'role': 'system', 'content': 'Follow the supplied Sentry evaluation schema. Return the requested JSON only.'},
            {'role': 'user', 'content': prompt}], repair=100, options=options)
        choice = result['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise RuntimeError('Incomplete Sentry model response')
        return choice['message']['content']


class SentryAdapter:
    def __init__(self, agent, provider, action_schema, log):
        from Sentry import SentryRunner
        from Sentry.config import SentryConfig, ModelConfig
        self.agent = agent; self.log = log
        self.runner = SentryRunner(AuditedJudge(provider), SentryConfig(
            model=ModelConfig(model=provider.model)),
            capture_runtime_events=True)
        # Host appends guidance to its existing actor, as the author integration
        # API permits; generate_repair() (paper's384-token actor) is not called.
        self.runner.start_task(objective='Complete the main task specified by public game dialogue within 300 environment actions. Use public observations to learn the task and rules.',
                               action_schema=action_schema)

    def observe(self, step, parsed, observation, terminal=False):
        from Sentry import agent_step_from_parts
        cycle = agent_step_from_parts(step_id=step, reasoning=parsed['reasoning'],
            raw_action=parsed['action'], tool_name='game', tool_args={'command': parsed['action']},
            observation=observation, parsed_ok=True, schema_valid=True,
            # Well-formed but infeasible commands are semantic failures, not
            # parser/schema failures. Unknown validity is explicitly supported.
            accepted_by_environment=None)
        repair = self.runner.step(cycle, terminal=terminal)
        if repair:
            self.agent.guidance = repair.prompt_text
        if terminal:
            self.runner.finalize()
        for event in self.runner.guard.drain_runtime_events():
            append_jsonl(self.log, event)
        return bool(repair)
