"""SCAR core: observe -> scoped evidence -> candidate check -> one execution gate.

The prompt and checked arms compute and expose the SAME decision packet. Only
the final gate differs. Missing certificates are UNKNOWN, never global bans.
This controller certifies neither the full natural-language goal nor survival.
"""
import copy
import json
import re
from time import perf_counter

from scar_public.causal_model import digest
from scar_public.obligation_agent import ObligationAgent
from scar_public.evidence import EVIDENCE_INSTRUCTION
from scar_public.viability import VIABILITY_INSTRUCTION
from scar_public.evidence_repair import RepairController
from scar_public.task_progress import ProgressMemory, ProgressController
from scar_public.task_outcome import reserve_check


CORE_INSTRUCTION = """
Plan towards the current public main task. Keep final task requirements distinct
from temporary methods and ingredients. You may receive a decision packet with
conditional plans, observed failures and remaining-resource checks. Interpret
UNKNOWN as missing evidence, not impossibility. Use a supported same-task plan
when useful, but address urgent threats. Only actual public feedback establishes
completion. Return reasoning, one action, and a frame with an EXACT goal_quote,
method, assessment and expected. resource_target is an optional concrete output.
"""


def gate(packet, proposed, mode, current_guard):
    """Pure, auditable sole execution switch. No fallback action is invented."""
    if mode not in ('prompt', 'checked'):
        raise ValueError(mode)
    candidate = packet.get('recommendation')
    reason = 'PROMPT_AUTHORITY'
    chosen = proposed
    if mode == 'checked':
        reason = 'NO_ADMITTED_CONTINUATION'
        if packet['guard'] != current_guard:
            reason = 'STALE_DECISION_PACKET'
        elif packet.get('combat'):
            reason = 'UNMODELED_COMBAT_YIELD'
        elif candidate:
            # A local resource planner cannot overrule combat, healing, dialogue
            # or an explicit write. Its intervention scope is part of the API.
            resource_action = proposed['action'].startswith(
                ('craft ', 'pick up ', 'take out ', 'store ', 'drop ', 'equip ', 'enter ', 'inspect ', 'wait'))
            if resource_action:
                if candidate['plan'][0] != proposed['action']:
                    chosen = {**proposed, 'action': candidate['plan'][0],
                              'resource_target': candidate['endpoint'],
                              'frame': {**proposed.get('frame', {}), 'goal_quote': candidate['task'],
                                        'method': 'Acquire ' + candidate['endpoint'] + ' for the quoted task'}}
                # Agreement is not an intervention: rewriting a frame or target
                # here would change future prompts despite an unchanged action.
                reason = 'CHECKED_SUPPORTED_FRAGMENT'
            else:
                reason = 'OUTSIDE_RESOURCE_INTERVENTION_SCOPE'
    return {**chosen, 'core_gate': dict(reason=reason, changed=chosen['action'] != proposed['action'],
                                      proposed=proposed['action'], packet_id=packet['id'])}


class CorePlannerAgent(ObligationAgent):
    """Shared perception/planning/LLM path with a switchable final authority."""
    def __init__(self, llm, system_prompt, mode='checked'):
        super().__init__(llm, system_prompt)
        self.system_prompt = (system_prompt.replace('exactly these keys', 'these required keys') +
                              EVIDENCE_INSTRUCTION + VIABILITY_INSTRUCTION + CORE_INSTRUCTION)
        self.notebook = ProgressMemory()
        self.controller = ProgressController(self.notebook)
        self.controller.mode = 'structured'
        self.controller.context_scope = 'attributes'
        self.controller.action_mode = 'observe'
        self.mode = mode
        self.max_steps = 300
        self.events = []
        self.guidance = ''

    def guard(self):
        m = self.notebook
        return digest(dict(current=m.model.current, tasks=m.progress_tasks,
                           evidence_revision=m.resource_evidence['revision'],
                           containers=m.model.containers, recipes=m.model.recipes))

    def decision_packet(self, proposal, text, step):
        started = perf_counter()
        m = self.notebook
        # Planning may record search attempts. Evaluate on a copy so an unchosen
        # proposal cannot fabricate observations, failed actions or commitment.
        shadow = copy.deepcopy(m)
        # Same-input packets must not depend on which arm received CPU first.
        # The existing1500-node limit remains; wall-clock cutoff is disabled only
        # for copied core candidate search, leaving frozen V16 unchanged.
        shadow.model.node_budget_only = True
        c = ProgressController(shadow)
        c.mode = 'structured'; c.context_scope = 'attributes'; c.max_steps = self.max_steps
        c.bind(proposal.get('task_quote') or proposal.get('frame', {}).get('goal_quote', ''))
        check = m.model.check_action(proposal['action'])
        review = c.review_proposal(proposal, text)
        focus = c.focus(proposal)
        candidates, rejected = [], []
        production = proposal['action'].startswith('craft ') or bool(proposal.get('resource_target'))
        if focus and production and 'I was attacked' not in text:
            candidates, rejected = c.alternatives(focus, text, step)
        admitted = []
        for candidate in candidates:
            reasons = []
            if not candidate['role_supported']:
                reasons.append('TASK_ROLE_UNRESOLVED')
            if candidate['reserve']['status'] not in ('NO_OTHER_EXPLICIT_OUTPUTS', 'JOINT_WITNESS_RETAINED'):
                reasons.append('REMAINING_MATERIAL_WITNESS_UNRESOLVED')
            first_check = m.model.check_action(candidate['plan'][0])
            if first_check['status'] == 'contradicted':
                reasons.append('FIRST_ACTION_CONTRADICTED')
            # A relaxed material witness is NOT a complete conditional policy.
            # The theorem applies only to its supported task/resource fragment.
            candidate['gate_obligations'] = dict(role=candidate['support'],
                reserves=candidate['reserve'], first_action=first_check,
                remaining_budget=self.max_steps-step, plan_cost=candidate['cost'],
                scope='Supported task/material fragment under faithful modeling; no whole-game certificate')
            if reasons:
                rejected.append(dict(endpoint=candidate['endpoint'], reasons=reasons))
            else:
                admitted.append(candidate)
        packet = dict(guard=self.guard(), proposal=proposal['action'], focus=focus,
            observed_check=check, evidence_rejection=review, candidates=candidates,
            rejected=rejected, recommendation=admitted[0] if admitted else None,
            combat='I was attacked' in text,
            semantics='UNKNOWN remains available to the LLM; automatic substitutions require all listed checks')
        packet['id'] = digest(packet)
        # Keep timing OUTSIDE prompts and hashes, otherwise matched arms diverge.
        return packet, (perf_counter()-started)*1000

    def act(self, obs):
        m = self.notebook; c = self.controller; step = self.llm.step
        text = obs['text']; prompt = m.prompt(text)
        # Only the action actually executed last turn contributes evidence.
        c.resume(text)
        m.refresh_tasks(); c.bind(m.frame.get('goal_quote', ''))
        prompt += RepairController.prepare_decision(c, text, step)
        prompt += '\nCurrent public task obligations:\n' + json.dumps(
            [dict(task=r['quote'], source=r['source']) for r in m.progress_tasks.values()], ensure_ascii=False)
        if self.guidance:
            prompt += '\nFailure-specific external guidance:\n' + self.guidance
            self.guidance = ''
        tokens = [0, 0]

        def query(p):
            result = self.llm.generate(p, self.system_prompt)
            tokens[0] += result['num_input_tokens']; tokens[1] += result['num_output_tokens']
            return json.loads(result['response'])

        proposed = query(prompt)
        packet, compute_ms = self.decision_packet(proposed, text, step)
        final = proposed
        informative = bool(packet['candidates'] or packet['evidence_rejection'] or
                           packet['observed_check']['status'] == 'contradicted')
        if informative:
            final = query(prompt + '\nDecision packet (same evidence and search in all arms):\n' +
                          json.dumps(packet, ensure_ascii=False, sort_keys=True) +
                          '\nReturn your final action. Conditional fragment support is not task completion.')
        executed = gate(packet, final, self.mode, self.guard())
        executed['decision_source'] = 'scar_core_gate' if executed['core_gate']['changed'] else 'scar_core_actor'
        executed['core_packet'] = packet
        executed['core_compute_ms'] = compute_ms
        executed['core_initial_proposal'] = proposed
        # Evidence learning is identical in both arms, and observes ACTUAL craft.
        RepairController.after_decision(c, executed, text, step)
        m.update(executed, text, step)
        self.events.append(dict(step=step, **executed['core_gate'], informative=informative,
                                recommendation=bool(packet['recommendation']), compute_ms=compute_ms))
        return executed['action'], *tokens, json.dumps(executed, ensure_ascii=False)

    def observe_terminal(self, obs):
        self.controller.resume(obs['text'])

