"""Boundary/causal validity checks, not tests of LLM scientific effectiveness."""
import copy
import json

import pytest

from scar_public.causal_model import CausalMonitor, ProposalError, project, outcome, predict, digest
from scar_public.causal_compiler import CompilationGap, search_fragment
from scar_public.causal_agent import CausalShadowAgent, CausalMemory
from scar_public.obligation_agent import ObligationAgent


def obs(held='no objects', ground='1 ore', extra='', place='Home, forge'):
    return (f'Current Location: {place}\nI am holding {held}.\nI have equipped no objects.\n'
            f'I see {ground} near me.\nNeighboring areas: store.\n' + extra)


def pickup(monitor, result='success', add=1000):
    return {'action': 'pick up ore', 'unresolved': ['capacity not independently established'],
            'hypotheses': [{'id': 'pickup', 'guard': [{'field': 'ground:ore', 'op': 'ge', 'value': 1000}],
                'effects': [{'field': 'holding:ore', 'op': 'add', 'value': add},
                            {'field': 'ground:ore', 'op': 'add', 'value': -add}],
                'result': result, 'unknowns': ['no unobserved impediment'],
                'evidence': [{'observation': 0, 'quote': 'I see 1 ore near me.'}]}]}


def make():
    monitor = CausalMonitor(); monitor.observe(obs())
    monitor.install(pickup(monitor), monitor.context('pick up ore'))
    return monitor


def test_missing_or_malformed_inventory_does_not_imply_zero():
    fields = {'holding:ore': 'numeric'}
    assert project('I am holding something unclear.', fields) == {}
    assert project('No inventory shown.', fields) == {}
    assert project('I am holding no objects.', fields) == {'holding:ore': 0}
    assert project('I am holding 0.5 ore.', fields) == {'holding:ore': 500}
    assert project('I am holding 0.0001 ore.', fields) == {}


def test_no_default_frame_or_zero_for_unknown_add():
    rule = {'guard': [], 'effects': [{'field': 'holding:ore', 'op': 'add', 'value': 1000}], 'result': 'unknown'}
    assert predict(rule, {}) == {}
    assert 'location' not in predict(rule, {'holding:ore': 0, 'location': 'Home'})


def test_operation_acceptance_does_not_predict_task_completion():
    assert outcome('I successfully crafted 1 sword. It is now on the ground.', 'craft 1 sword') == 'success'
    assert outcome('Stage completed: Find the ore.', 'pick up ore') is None
    assert outcome('Cannot craft a single sword. Do not have sufficient amount of necessary ingredients.',
                   'craft 1 sword') == 'failure'
    assert outcome('Cannot enter hall, the door is locked.', 'enter hall') == 'failure'


def test_future_citation_and_stale_context_are_rejected_atomically():
    m = CausalMonitor(); m.observe(obs()); ctx = m.context('pick up ore'); p = pickup(m)
    p['hypotheses'][0]['evidence'] = [{'observation': 1, 'quote': 'I picked up ore.'}]
    with pytest.raises(ProposalError): m.install(p, ctx)
    assert m.version == 0 and not m.rules
    m.observe(obs(extra='I waited.'), 'wait')
    with pytest.raises(ProposalError): m.install(pickup(m), ctx)


def test_counterexample_invalidates_cert_and_renaming_does_not_repair():
    m = make()
    cert = search_fragment(m, ['pick up ore'], [{'field': 'holding:ore', 'op': 'ge', 'value': 1000}],
                           {'holding:ore': 2000, 'ground:ore': 1000}, horizon=1)
    assert cert['status'] == 'CONDITIONAL_PLAN_FOUND' and cert['valid']
    prediction = m.prepare('pick up ore'); version = m.version
    event = m.observe(obs(extra='Cannot pick up ore, not enough space in hand.'), 'pick up ore')
    assert event['checks'][0]['verdict'] == 'contradicted'
    assert m.version == version+1 and not cert['valid']
    assert prediction['version'] == version and m.rules['pick up ore'][0]['status'] == 'rejected'
    replacement = pickup(m); replacement['hypotheses'][0]['id'] = 'renamed'
    with pytest.raises(ProposalError): m.install(replacement, m.context('pick up ore'))
    replacement = pickup(m, 'failure', 0)
    m.install(replacement, m.context('pick up ore'))
    assert m.version == version+2


def test_unknown_feedback_is_not_a_counterexample_or_confirmation():
    m = make(); m.prepare('pick up ore'); old = m.version
    e = m.observe('The world becomes dark.', 'pick up ore')
    assert e['checks'][0]['verdict'] == 'unobserved' and m.version == old


def test_unexecuted_prediction_cannot_update_model():
    m = make(); m.prepare('pick up ore'); old = m.version
    m.observe(obs(extra='I waited.'), 'wait')
    assert m.version == old and m.events[-1]['kind'] == 'discarded_prediction'


def test_projection_of_text_requires_fresh_inspection():
    m = CausalMonitor(); m.observe(obs(extra='I inspected note: paper.\nIt writes: OLD'))
    assert m.current['text:note'] == 'OLD'
    m.observe(obs(extra='I wrote on note: NEW'), 'write NEW note')
    assert 'text:note' not in m.current


def test_common_policy_cannot_assume_successful_hypothesis_only():
    m = make()
    p = pickup(m); alternative = pickup(m, 'failure', 0)['hypotheses'][0]
    alternative['id'] = 'blocked'; p['hypotheses'].append(alternative)
    m.install(p, m.context('pick up ore'))
    c = search_fragment(m, ['pick up ore'], [{'field': 'holding:ore', 'op': 'ge', 'value': 1000}],
                        {'holding:ore': 2000, 'ground:ore': 1000}, horizon=1)
    assert c['status'] == 'UNKNOWN_FOR_ENVIRONMENT' and c['worlds'] == 2


def test_omitted_effect_is_unknown_in_compiler_instead_of_frame():
    m = make(); p = pickup(m)
    p['hypotheses'][0]['effects'] = p['hypotheses'][0]['effects'][:1]
    m.install(p, m.context('pick up ore'))
    c = search_fragment(m, ['pick up ore'], [{'field': 'holding:ore', 'op': 'ge', 'value': 1000}],
                        {'holding:ore': 2000, 'ground:ore': 1000}, horizon=1)
    assert c['status'] == 'UNKNOWN_FOR_ENVIRONMENT'


def test_finite_grounding_and_observation_gaps_are_reported():
    m = make()
    with pytest.raises(CompilationGap):
        search_fragment(m, ['pick up ore'], [{'field': 'holding:ore', 'op': 'ge', 'value': 1}],
                        {'holding:ore': 1000000, 'ground:ore': 1000000}, horizon=2)
    with pytest.raises(CompilationGap):
        search_fragment(m, ['unsupported'], [{'field': 'holding:ore', 'op': 'ge', 'value': 1000}], {})


def test_state_roundtrip_preserves_pending_prediction_and_invalidations():
    m = make(); p = m.prepare('pick up ore')
    restored = CausalMonitor.load(json.loads(json.dumps(m.state())))
    assert restored.pending == p and restored.prefix_hash == m.prefix_hash
    e = restored.observe(obs(held='1 ore', ground='no objects', extra='I picked up ore.'), 'pick up ore')
    assert e['checks'][0]['verdict'] == 'matched'
    assert restored.rules['pick up ore'][0]['status'] == 'candidate'  # One match does not prove a rule.


def test_history_gate_rejects_sourced_but_refuted_rule_before_new_execution():
    m = CausalMonitor(); m.observe(obs())
    m.observe(obs(extra='Cannot pick up ore, not enough space in hand.'), 'pick up ore')
    m.install(pickup(m), m.context('pick up ore'))
    assert m.rules['pick up ore'][0]['status'] == 'rejected_by_public_history'
    assert m.prepare('pick up ore')['predictions'] == []
    assert m.admission_checks[-1]['conflicts'][0]['after_observation'] == 1


def test_prior_matching_result_does_not_establish_causal_explanation():
    m = CausalMonitor(); m.observe(obs())
    m.observe(obs(extra='Cannot pick up ore, not enough space in hand.'), 'pick up ore')
    p = pickup(m, 'failure', 0)
    m.install(p, m.context('pick up ore'))
    assert m.rules['pick up ore'][0]['status'] == 'candidate'
    assert not m.admission_checks[-1]['conflicts']


def test_certificate_requires_same_prefix_even_without_counterexample():
    m = make()
    c = search_fragment(m, ['pick up ore'], [{'field': 'holding:ore', 'op': 'ge', 'value': 1000}],
                        {'holding:ore': 2000, 'ground:ore': 1000}, horizon=1)
    assert m.certificate_is_current(c)
    m.prepare('pick up ore')
    m.observe(obs(held='1 ore', ground='no objects', extra='I picked up ore.'), 'pick up ore')
    assert not m.certificate_is_current(c)


def test_transition_examples_only_use_prefix_and_keep_exact_source_indices():
    m = CausalMonitor(); m.observe(obs())
    m.observe(obs(held='1 ore', ground='no objects', extra='I picked up ore.'), 'pick up ore')
    context = m.context('pick up ore')
    assert len(context['observed_transitions']) == 1
    example = context['observed_transitions'][0]
    assert example['before']['holding:ore'] == 0 and example['after']['holding:ore'] == 1000
    assert example['after_observation'] < context['prefix_observations']


class Actor:
    step = 0
    def __init__(self): self.prompts = []
    def generate(self, prompt, system):
        self.prompts.append((prompt, system))
        return {'response': json.dumps({'reasoning': 'Pick up the observed ore.', 'action': 'pick up ore'}),
                'num_input_tokens': 2, 'num_output_tokens': 2}
    def request(self, messages):
        ctx = json.loads(messages[-1]['content'])
        m = CausalMonitor(); m.observe(obs())
        p = pickup(m)
        assert ctx['action'] == p['action']
        return {'choices': [{'message': {'content': json.dumps(p)}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 5, 'completion_tokens': 5}}


def test_shadow_preserves_v6_actor_prompt_actions_and_reload():
    plain, shadow = ObligationAgent(Actor(), 'Act.'), CausalShadowAgent(Actor(), 'Act.')
    observation = {'text': obs()}
    a = plain.act(observation); b = shadow.act(observation)
    assert a[0] == b[0] and plain.llm.prompts == shadow.llm.prompts
    assert b[1:3] == (7, 7)
    assert json.loads(b[3])['causal_shadow']['fragment']['status'] == 'CONDITIONAL_PLAN_FOUND'
    checkpoint = json.loads(json.dumps(shadow.notebook.state()))
    resumed = CausalShadowAgent(Actor(), 'Act.'); resumed.notebook.load(checkpoint)
    next_obs = {'text': obs(held='1 ore', ground='no objects', extra='I picked up ore.')}
    plain.llm.step = resumed.llm.step = 1
    assert plain.act(next_obs)[0] == resumed.act(next_obs)[0]
    assert plain.llm.prompts[-1] == resumed.llm.prompts[-1]
    assert resumed.notebook.causal.events[-1]['kind'] == 'feedback'
    assert resumed.notebook.causal.events[-1]['checks'][0]['verdict'] == 'matched'


def test_final_observation_is_evaluated_once_and_checkpoint_can_resume():
    agent = CausalShadowAgent(Actor(), 'Act.')
    agent.act({'text': obs()})
    final = {'text': obs(held='1 ore', ground='no objects', extra='I picked up ore.')}
    agent.observe_terminal(final); agent.observe_terminal(final)
    assert len(agent.notebook.causal.observations) == 2
    cp = json.loads(json.dumps(agent.notebook.state()))
    restored = CausalShadowAgent(Actor(), 'Act.'); restored.notebook.load(cp)
    restored.llm.step = 1
    restored.act(final)
    assert len(restored.notebook.causal.observations) == 2


@pytest.mark.parametrize('mutation', [
    lambda p: p['hypotheses'][0]['effects'].append({'field': 'invented:oracle', 'op': 'same'}),
    lambda p: p['hypotheses'][0]['effects'].append({'field': 'location', 'op': 'add', 'value': 1}),
    lambda p: p['hypotheses'][0]['effects'].append({'field': ['bad'], 'op': 'same'}),
    lambda p: p['hypotheses'][0]['effects'].append({'field': 'holding:ore', 'op': 'same'}),
    lambda p: p['hypotheses'][0]['guard'].append({'field': 'holding:ore', 'op': 'ge', 'value': True}),
])
def test_malformed_or_unexpressible_llm_outputs_fail_closed(mutation):
    m = CausalMonitor(); m.observe(obs()); p = pickup(m); mutation(p)
    with pytest.raises(ProposalError): m.install(p, m.context('pick up ore'))
    assert not m.rules and m.version == 0
