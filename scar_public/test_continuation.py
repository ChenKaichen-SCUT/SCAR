import copy
import json

from scar_public.continuation import ContinuationMemory, ContinuationAgent, select_repair
from scar_public.core_planner import CorePlannerAgent


def obs(place='hall', held='no objects', ground='1 note', feedback='', neighbors='vault, yard'):
    return (f'Current Time: 0001-01-01 10:00:00\nCurrent Location: Estate, {place}\n'
            f'{feedback}\nI am holding {held}.\nI have equipped no objects.\n'
            f'I see {ground} near me.\nI see guide nearby.\nMy health is at 100.\n'
            f'Neighboring areas: {neighbors}.\n')


def fail_memory():
    m = ContinuationMemory()
    m.observe(obs(), 0); m.commit('enter vault', 'goal')
    m.observe(obs(feedback='Cannot enter vault, the door is locked.'), 1)
    return m


def test_actual_failure_changes_eligibility_without_treating_unknown_as_failure():
    m = fail_memory()
    assert m.assess('enter vault', 'goal')['kind'] == 'REPEATED_OBSERVED_FAILURE'
    assert m.assess('enter yard', 'goal') is None
    assert m.assess('enter vault', 'different task') is None


def test_changed_resources_information_and_expiry_restore_retry():
    for text, step in [(obs(held='1 key'), 2),
                       (obs(feedback='guide says: The vault is open now.'), 2),
                       (obs(), 7)]:
        m = fail_memory(); m.observe(text, step)
        assert m.assess('enter vault', 'goal') is None


def test_unknown_state_is_not_empty_state():
    m = fail_memory(); m.observe('Current Location: Estate, hall', 2)
    assert m.assess('enter vault', 'goal') is None


def test_successful_repetition_and_urgent_actions_are_not_suppressed():
    for action in ['attack opponent', 'defend', 'eat bread', 'craft 1 rod', 'pick up rod', 'wait']:
        m = ContinuationMemory()
        for i in range(6):
            m.observe(obs(), i)
            assert m.assess(action, 'goal') is None
            m.commit(action, 'goal')
    m = fail_memory()
    m.observe(obs(feedback='I was attacked by opponent and lost 3 HP.'), 2)
    assert m.assess('enter vault', 'goal') is None


def test_repeated_route_requires_two_completed_nonprogress_repetitions():
    m = ContinuationMemory(); m.observe(obs(), 0)
    for i, place in enumerate(['yard', 'hall', 'yard', 'hall', 'yard', 'hall'], 1):
        m.commit('enter '+place, 'goal')
        m.observe(obs(place=place, neighbors='hall' if place=='yard' else 'vault, yard'), i)
    assert m.assess('enter yard', 'goal')['kind'] == 'REPEATED_WITHOUT_OBSERVED_PROGRESS'
    # Returning with a needed object is useful transit, not the old loop.
    m.observe(obs(held='1 key'), 7)
    assert m.assess('enter yard', 'goal') is None


def test_new_dialogue_content_and_task_completion_invalidate_old_repetition():
    m = ContinuationMemory()
    for i in range(4):
        m.observe(obs(feedback='guide says: Visit the vault.'), i)
        m.commit('talk to guide', 'goal')
    m.observe(obs(feedback='guide says: Visit the vault.'), 4)
    assert m.assess('talk to guide', 'goal')
    m.commit('talk to guide', 'goal')
    m.observe(obs(feedback='Stage completed: Visit the vault.'), 5)
    assert m.assess('talk to guide', 'goal') is None


def repair_fixture():
    m = fail_memory()
    original = dict(action='enter vault', reasoning='old', frame=dict(goal_quote='Visit the vault.', method='old'))
    packet = dict(epoch=m.epoch, context=m.context(original['action'], 'goal'),
                  trigger=m.assess(original['action'], 'goal'), goals=['Visit the vault.'],
                  options=['enter vault', 'enter yard', 'talk to guide'],
                  public_support='Neighboring areas: vault, yard.\nguide says: Visit the vault.')
    candidate = dict(action='enter yard', reasoning='Find another route', goal_quote='Visit the vault.',
                     support_quote='Neighboring areas: vault, yard.', expected='Observe another exit.')
    return m, original, packet, candidate


def test_gate_selects_supported_alternative_when_actor_repeats_known_failure():
    m, original, packet, candidate = repair_fixture()
    response = {**candidate, 'action':'enter vault', 'alternatives':[candidate]}
    left, le = select_repair(original, response, packet, m, 'goal', 'advice')
    right, re = select_repair(original, response, packet, m, 'goal', 'repair')
    assert left == original and not le['changed']
    assert right['action'] == 'enter yard' and re['changed']
    assert re['rejected'][0]['reasons'] == ['REPEATED_OBSERVED_FAILURE']


def test_unsupported_consumption_malformed_action_and_stale_packet_abstain():
    for edits in [dict(action='drop key'), dict(action=['enter yard'])]:
        m, original, packet, candidate = repair_fixture()
        result, event = select_repair(original, {**candidate, **edits}, packet, m, 'goal')
        assert result == original and not event['changed']
    m, original, packet, candidate = repair_fixture()
    m.observe(obs(held='1 key'), 2)
    assert select_repair(original, candidate, packet, m, 'goal')[1]['reason'] == 'STALE_REPAIR_PACKET'


def test_goal_is_preserved_without_requiring_llm_to_retranslate_it():
    m, original, packet, candidate = repair_fixture()
    result,event=select_repair(original,dict(action='enter yard',reasoning='Seek another route'),packet,m,'goal')
    assert event['changed'] and result['frame']['goal_quote']==original['frame']['goal_quote']


def test_cycle_warning_does_not_forbid_necessary_transit_or_repeat_queries():
    m = ContinuationMemory(); m.observe(obs(),0)
    for i,place in enumerate(['yard','hall','yard','hall','yard','hall'],1):
        m.commit('enter '+place,'goal');m.observe(obs(place=place),i)
    trigger=m.assess('enter yard','goal')
    assert trigger and not m.offered(trigger)
    original=dict(action='enter yard',frame=dict(goal_quote='Visit the vault.'))
    packet=dict(epoch=m.epoch,context=m.context('enter yard','goal'),trigger=trigger,
                goals=['Visit the vault.'],options=['enter yard'],public_support='')
    result,event=select_repair(original,dict(action='enter yard',reasoning='Necessary transit'),packet,m,'goal')
    assert result==original and not event['changed']
    m.mark_offered(trigger)
    assert m.offered(trigger)


def test_first_line_inspection_content_counts_as_information():
    m=ContinuationMemory();m.observe(obs(),0);m.commit('inspect note','goal')
    m.observe(obs(feedback='I inspected note: A message revealing a new path.'),1)
    assert m.last_outcome['progress']
    assert 'I inspected note: A message revealing a new path.' in m.facts


def test_entity_renaming_does_not_change_failure_deferral_or_release():
    # Metamorphic check, not a claim of transfer to a new game family.
    for label in ['sealed_gate', 'node_51', 'workroom', 'checkpoint_x']:
        m=ContinuationMemory()
        text=obs(neighbors=label+', yard')
        m.observe(text,0);m.commit('enter '+label,'goal')
        m.observe(obs(neighbors=label+', yard',feedback=f'Cannot enter {label}, the door is locked.'),1)
        assert m.assess('enter '+label,'goal')['kind']=='REPEATED_OBSERVED_FAILURE'
        m.observe(obs(neighbors=label+', yard',held='1 changed_resource'),2)
        assert m.assess('enter '+label,'goal') is None


def test_nonexecuted_candidates_never_become_failure_evidence():
    m, original, packet, candidate=repair_fixture()
    before=copy.deepcopy(m.state())
    select_repair(original,candidate,packet,m,'goal')
    assert m.state()==before
    assert not any(r['action']=='enter yard' for r in m.records)


def test_untriggered_agent_preserves_actor_prompts_actions_frames_and_memory():
    class LLM:
        step = 0
        def __init__(self): self.prompts = []
        def generate(self, user, system):
            self.prompts.append((system, user))
            return dict(response=json.dumps(dict(action='talk to guide', reasoning='Ask for task',
                frame=dict(goal_quote='Visit the vault.', method='Ask guide', assessment='Pending', expected='Get instructions'))),
                num_input_tokens=1, num_output_tokens=1)
    base, repaired = CorePlannerAgent(LLM(), 'Return JSON.'), ContinuationAgent(LLM(), 'Return JSON.')
    text = obs(feedback='guide says: Visit the vault.')
    for i in range(2):
        for agent in (base, repaired): agent.llm.step = i
        a, b = base.act(dict(text=text)), repaired.act(dict(text=text))
        assert a[:3] == b[:3]
        assert base.llm.prompts == repaired.llm.prompts
        assert base.notebook.state() == repaired.notebook.state()
        assert not json.loads(b[3])['continuation']['changed']
