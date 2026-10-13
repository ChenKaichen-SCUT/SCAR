"""Conditional arbitration. No extra LLM ranking or new exploration policy."""
from scar_v3.state import parse_action


def choose(controller, proposal, candidate, checks):
    base, s1 = checks['llm'], checks['bounded_controller']
    if proposal == candidate:
        return candidate, 'same_action'
    if s1['status'] == 'REJECT' and base['status'] != 'REJECT':
        return proposal, 'controller_public_precondition_or_consequence_rejected'
    if base['status'] == 'REJECT' and s1['status'] != 'REJECT':
        return candidate, 'retain_controller_correction_of_rejected_llm'
    b, c = parse_action(proposal), parse_action(candidate)
    # Publicly observed ongoing carrying damage plus relevant discard is useful
    # evidence. It is not justified by an LLM explanation alone.
    last = controller.consequences.last_carry
    if last and last.get('risk_item') == b.target and b.verb in ('discard', 'drop') and base['status'] != 'REJECT':
        if c.verb not in ('discard', 'drop'):
            return proposal, 'observed_carrying_damage_supports_llm_removal_trial'
    if base['known_goal_progress'] and c.verb in ('inspect', 'wait') and s1['status'] != 'SUPPORTED':
        return proposal, 'known_goal_execution_over_uncertified_passive_candidate'
    return candidate, 'retain_structured_default_when_evidence_does_not_resolve'
