import copy
import pytest
from scar_public.sentry_persistent import apply_choice, fingerprint
from scar_public.sentry_selective import SelectiveRepair, replacement_allowed
from scar_public.test_sentry_persistent import Provider, SYSTEM, OBS, card


def verdict():
    refs=[dict(cycle=0,quote='The passage is locked.')]
    return dict(candidates=[dict(id='A',purpose='Preparation for entering chamber',status='blocked',defect_kind='failed_precondition',
        condition='Passage locked',evidence=copy.deepcopy(refs)),
        dict(id='B',purpose='Learn access conditions',status='supported',defect_kind='none',condition='Plate visible here',evidence=copy.deepcopy(refs))],
        relations=[dict(blocked='A',alternative='B',addresses_issue=True,how='Read whether a key or code is needed, then seek the indicated one',
            resources='preserved',resource_reason='Inspection consumes no known task item',evidence=copy.deepcopy(refs))])


def controller(outputs):
    control=SelectiveRepair(Provider(outputs),SYSTEM);control.seed(OBS)
    control.records.append(dict(cycle=0,action='enter chamber',observation=OBS))
    control.pending=dict(step=1,observation_hash=fingerprint(OBS),card=card())
    return control


def test_replacement_requires_specific_supported_defect_and_targeted_ready_alternative():
    c=controller([verdict()]);p=dict(action='enter chamber',reasoning='Try again')
    assert c.choose(1,OBS,p)['action']=='inspect plate' and c.comparisons==1


@pytest.mark.parametrize('mutation',[
    lambda v:v['candidates'][0].update(status='supported',defect_kind='none'),
    lambda v:v['relations'][0].update(addresses_issue=False),
    lambda v:v['candidates'][1].update(status='unknown'),
    lambda v:v['relations'][0].update(resources='conflict'),
    lambda v:v['relations'][0].update(resources='unknown'),
    lambda v:v.update(relations=[]),
])
def test_uncertainty_or_preparation_preserves_entire_original_response(mutation):
    v=verdict();mutation(v);c=controller([v]);p=dict(action='enter chamber',reasoning='  Original reason.  ',extra='kept')
    assert c.choose(1,OBS,p) is p


def test_false_citation_rejected_without_retry_or_rewriting():
    v=verdict();v['candidates'][0]['evidence']=[dict(cycle=0,quote='The passage is open.')]
    c=controller([v]);p=dict(action='enter chamber',reasoning='Original')
    assert c.choose(1,OBS,p) is p and c.comparisons==1
    assert c.events[-1]['selection_reason']=='invalid_comparison'


def test_historical_support_alone_cannot_establish_current_applicability():
    v=verdict();v['candidates'][1]['evidence'][0]['cycle']=-1
    with pytest.raises(ValueError,match='current alternative'):replacement_allowed(v,[dict(cycle=-1,observation=OBS),dict(cycle=0,observation=OBS)])


@pytest.mark.parametrize('step,observation,action',[(1,OBS,'inspect plate'),(1,OBS,' inspect plate '),(2,OBS,'enter chamber'),(1,'Changed state','enter chamber')])
def test_equal_actions_and_stale_cases_use_no_comparison_call(step,observation,action):
    c=controller([]);p=dict(action=action,reasoning='Original')
    assert c.choose(step,observation,p) is p and c.comparisons==0


def test_budget_exhaustion_preserves_behavior():
    c=controller([]);c.max_comparisons=0;p=dict(action='enter chamber',reasoning='Original')
    assert c.choose(1,OBS,p) is p and c.comparisons==0


def test_apply_noop_preserves_memory_byte_for_byte_even_with_new_reason():
    class Actor:memory='Do not rewrite this history\n'
    class EqualController:
        def choose(self,*args):return dict(action='wait',reasoning='NEW REASON')
    actor=Actor();before=actor.memory;p=dict(action='wait',reasoning=' Original  ',metadata='untouched')
    assert apply_choice(actor,1,OBS,p,EqualController()) is p
    assert actor.memory==before


def test_candidate_role_swap_uses_identical_request_and_asymmetric_execution():
    v=verdict();forward=controller([v]);reverse=controller([v])
    reverse.pending['card']['next']['action']='enter chamber'
    p=dict(action='enter chamber',reasoning='Persuasive but unsupported story')
    assert forward.choose(1,OBS,p)['action']=='inspect plate'
    q=dict(action='inspect plate',reasoning='Different persuasive story')
    assert reverse.choose(1,OBS,q) is q
    assert forward.provider.prompts==reverse.provider.prompts


def test_two_supported_candidates_do_not_create_a_ranking_override():
    v=verdict();v['candidates'][0].update(status='supported',defect_kind='none')
    assert replacement_allowed(v,[dict(cycle=0,observation=OBS)])[0] is False
