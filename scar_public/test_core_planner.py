import copy
import json
from scar_public.core_planner import CorePlannerAgent, gate
from scar_public.test_task_outcome import scenario
from scar_public.task_progress import ProgressMemory


def packet():
    return dict(id='p', guard='g', combat=False,
                recommendation=dict(plan=['pick up wood'], endpoint='club', task='Obtain a weapon.'))


def test_single_gate_changes_authority_without_changing_packet():
    p = packet(); original = copy.deepcopy(p)
    proposal = dict(action='craft 1 splint', reasoning='try', frame={})
    assert gate(p, proposal, 'prompt', 'g')['action'] == proposal['action']
    assert gate(p, proposal, 'checked', 'g')['action'] == 'pick up wood'
    assert p == original and proposal['action'] == 'craft 1 splint'


def test_stale_epoch_or_combat_never_executes_old_recommendation():
    p = packet(); proposal = dict(action='craft 1 club')
    assert gate(p, proposal, 'checked', 'new')['core_gate']['reason'] == 'STALE_DECISION_PACKET'
    p['combat'] = True
    assert gate(p, proposal, 'checked', 'g')['action'] == proposal['action']


def test_unknown_is_not_a_global_ban_and_healing_is_not_overridden():
    p = packet(); proposal = dict(action='eat bread')
    assert gate(p, proposal, 'checked', 'g')['action'] == 'eat bread'
    p['recommendation'] = None
    proposal = dict(action='craft 1 unknown')
    assert gate(p, proposal, 'checked', 'g')['action'] == proposal['action']


def test_agreement_preserves_every_actor_field_not_only_command():
    p=packet();proposal=dict(action='pick up wood',reasoning='Collect material',
                           frame=dict(goal_quote='Obtain a weapon.',method='My original method'))
    a=gate(p,proposal,'prompt','g');b=gate(p,proposal,'checked','g')
    assert not b['core_gate']['changed']
    assert {k:v for k,v in a.items() if k!='core_gate'}=={k:v for k,v in b.items() if k!='core_gate'}
    assert 'resource_target' not in b


def fixture():
    old, _, task, text = scenario()
    agent = CorePlannerAgent(None, 'Return JSON.')
    m = ProgressMemory()
    m.__dict__.update(copy.deepcopy(old.__dict__))
    m.progress_tasks = {'guide': dict(quote=task, block=task, aliases=[task], source=task)}
    agent.notebook = m
    return agent, task, text


def test_plan_preview_cannot_modify_evidence_or_create_an_execution():
    agent, task, text = fixture()
    before = copy.deepcopy(agent.notebook.state())
    p, _ = agent.decision_packet(dict(action='craft 1 splint', resource_target='splint',
                                     frame={'goal_quote': task}), text, 10)
    assert agent.notebook.state() == before
    assert p['recommendation']['endpoint'] == 'club'
    assert p['recommendation']['gate_obligations']['scope'].startswith('Supported task/material fragment')


def test_unsupported_role_and_missing_material_witness_are_not_admitted():
    agent, task, text = fixture()
    agent.notebook.model.source_lines = []
    p, _ = agent.decision_packet(dict(action='craft 1 splint', resource_target='splint',
                                     frame={'goal_quote': task}), text, 10)
    assert p['recommendation'] is None


def test_computation_timing_not_in_prompt_packet():
    agent, task, text = fixture()
    proposal = dict(action='craft 1 splint', resource_target='splint', frame={'goal_quote': task})
    a, _ = agent.decision_packet(proposal, text, 10)
    b, _ = agent.decision_packet(proposal, text, 10)
    assert a == b
    assert 'compute_ms' not in json.dumps(a)


def test_actual_arms_receive_identical_prompts_and_only_gate_changes_action():
    class FakeLLM:
        step = 10
        def __init__(self, task): self.prompts=[]; self.task=task
        def generate(self, user, system):
            self.prompts.append((system,user))
            return dict(response=json.dumps(dict(action='craft 1 splint',reasoning='Try a recipe',
                resource_target='splint',frame=dict(goal_quote=self.task,method='Craft splint',
                assessment='Pending',expected='Get a weapon'))),num_input_tokens=1,num_output_tokens=1)
    a,task,text=fixture(); b=copy.deepcopy(a)
    a.mode='prompt';b.mode='checked'
    from scar_public.task_progress import ProgressController
    for agent in (a,b):
        agent.controller=ProgressController(agent.notebook)
        agent.controller.mode='structured';agent.controller.context_scope='attributes'
        agent.controller.action_mode='observe';agent.llm=FakeLLM(task)
    obs=dict(text=text+'\n\nguide says: '+task,step=10)
    left=a.act(obs);right=b.act(obs)
    assert a.llm.prompts==b.llm.prompts and len(a.llm.prompts)==2
    assert left[0]=='craft 1 splint' and right[0]=='pick up wood'
    assert a.notebook.last_action==left[0] and b.notebook.last_action==right[0]
