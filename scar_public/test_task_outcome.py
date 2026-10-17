import copy,json
from scar_public.task_outcome import OutcomeMemory,OutcomeController,reserve_check,remaining_obligations,repair_preview
from scar_public.test_action_repair import fixture


def scenario():
    m=OutcomeMemory();c=OutcomeController(m);task='Obtain a weapon.'
    text='[1] '+task+'\nCurrent Location: room\nI am holding 1 wood.\nI have equipped no objects.\nI see 1 wood, 1 bench near me.'
    m.prompt(text);m.model.capacity_lower=m.model.capacity_upper=3
    m.model.recipes={'splint':{'needs':{'wood':1},'quote':'splint (1 wood)'},'club':{'needs':{'wood':2},'quote':'club (2 wood)'}}
    m.model.source_lines.append('I inspected club: A basic weapon.')
    m.frame={'goal_quote':task,'method':'Craft splint'}
    return m,c,task,text


def test_supported_task_endpoint_beats_shorter_unsupported_product():
    m,c,task,text=scenario()
    candidates,_=c.alternatives(dict(task=task,target='splint'),text,10)
    assert candidates[0]['endpoint']=='club' and candidates[0]['role_supported']
    assert next(r for r in candidates if r['endpoint']=='splint')['cost']<candidates[0]['cost']


def test_unknown_role_allows_bounded_trial_instead_of_global_ban():
    m,c,task,text=scenario();m.model.source_lines=[l for l in m.model.source_lines if 'I inspected' not in l]
    row=c.decision(dict(task=task,target='splint'),text,10)
    assert row['chosen']['endpoint']=='splint' and not row['chosen']['role_supported']


def test_insufficient_remaining_budget_declines_endpoint_commitment():
    m,c,task,text=scenario()
    rows,_=c.alternatives(dict(task=task,target='splint'),text,299)
    assert not rows


def test_witness_loss_defers_consumption_without_claiming_impossibility():
    m,c,task,text=scenario();other='Craft a key and hold it in your hands.'
    m.model.recipes['key']={'needs':{'wood':2},'quote':'key (2 wood)'}
    m.model.tasks.append(other);m.model.known_tasks.append(other);m.model.source_lines.append('[2] '+other)
    r=reserve_check(m.model,task,'club',['pick up wood','craft 1 club','pick up club'])
    assert r['status']=='JOINT_WITNESS_NOT_REESTABLISHED'
    assert r['before']['status']=='JOINT_MATERIAL_WITNESS' and 'inconclusive' in r['qualification']


def test_existing_goal_inputs_are_not_terminal_reservations():
    m,c,task,text=scenario();m.model.tasks=[task]
    assert remaining_obligations(m.model,task,'club')==[]
    assert reserve_check(m.model,task,'club',['craft 1 club'])['status']=='NO_OTHER_EXPLICIT_OUTPUTS'


def test_known_output_held_does_not_become_task_success():
    m,c,task,text=scenario();m.model.current['holding']={'club':1}
    candidates,rejected=c.alternatives(dict(task=task,target='club'),text,10)
    assert not candidates and rejected[0]['reason']=='ENDPOINT_HELD_TASK_FEEDBACK_REQUIRED'
    assert task not in m.model.completed


def test_capacity_retrieval_requires_a_conditional_endpoint_suffix():
    m,c,text,review=fixture();event=c.compile_repair(review,text,10)
    m.model.acquisition=lambda *a,**kw:{'status':'unknown'}
    assert repair_preview(m.model,event) is None


def test_identical_possession_requirements_do_not_invent_extra_copies():
    m,c,task,text=scenario();other='Hold club in your hands.'
    m.model.tasks.append(other);m.model.known_tasks.append(other);m.model.source_lines.append('[2] '+other)
    m.model.current.update(holding={'club':1},ground={});m.model.recipes={}
    r=reserve_check(m.model,task,'club',[])
    assert r['status']=='JOINT_WITNESS_RETAINED'


def test_repeated_physical_state_releases_automatic_endpoint():
    m,c,task,text=scenario();choice=c.decision(dict(task=task,target='splint'),text,10)['chosen'];c.emit_choice(choice,10)
    c.method_condition_step(text,11);c.method_condition_step(text,12);c.method_condition_step(text,13)
    assert any(r.get('reason')=='OBSERVED_FAILURE_OR_NO_TASK_PROGRESS' for r in m.outcome_decisions)


def test_public_goal_change_releases_old_commitment():
    m,c,task,text=scenario();c.emit_choice(c.decision(dict(task=task,target='splint'),text,10)['chosen'],10)
    m.model.tasks=[];m.intent_tasks={}
    assert c.method_condition_step(text,11) is None
    assert m.outcome_focus is None and m.resource_target==''


def test_checkpoint_preserves_outcome_decisions_and_trial_allowance():
    m,c,task,text=scenario();c.emit_choice(c.decision(dict(task=task,target='splint'),text,10)['chosen'],10)
    n=OutcomeMemory();n.load(json.loads(json.dumps(m.state())))
    assert n.outcome_focus==m.outcome_focus and n.outcome_lease==m.outcome_lease


def test_previous_public_method_can_recover_focus_after_target_cleared():
    m,c,task,text=scenario();m.action_goal_bindings={'club':{'task':task,'step':1}}
    focus=c.focus(dict(action='',frame={'goal_quote':'Explore the world','method':'Craft club'}))
    assert focus=={'task':task,'target':'club'}


def test_candidate_preview_cannot_mark_unexecuted_inspections_as_attempted(monkeypatch):
    from scar_public.obligations import ExecutionModel
    m,c,task,text=scenario()
    def search(self,target,**kwargs):
        self.discovery_checks.append({'target':target,'item':'bench'})
        return {'status':'unknown'}
    monkeypatch.setattr(ExecutionModel,'acquisition',search)
    before=copy.deepcopy(m.model.discovery_checks);c.alternatives(dict(task=task,target='splint'),text,10)
    assert m.model.discovery_checks==before


def test_guarded_repair_cannot_bypass_the_task_choice_gate(monkeypatch):
    m,c,task,text=scenario()
    monkeypatch.setattr(c,'decision',lambda *a:{'chosen':None})
    monkeypatch.setattr(c,'bounded_probe',lambda *a:None)
    assert c.certified_repair({'original_task':task,'action':'craft 1 splint'},text,10) is None
    assert m.action_program is None


def test_literal_role_counterevidence_supersedes_previous_positive_type():
    m,c,task,text=scenario();m.model.source_lines.append('I inspected club: This is not a weapon.')
    rows,rejected=c.alternatives(dict(task=task,target='club'),text,10)
    assert not rows and any(r['reason']=='EXPLICIT_ROLE_CONTRADICTION' for r in rejected)


def test_rejecting_a_subtype_does_not_refute_the_broader_task_role():
    from scar_public.task_outcome import task_role
    m,c,task,text=scenario();m.model.source_lines.append('I inspected club: Not a ceremonial weapon, but useful in a fight.')
    assert task_role(m.model,'club',task)['status']!='EXPLICIT_ROLE_CONTRADICTION'


def test_an_explicit_named_task_output_need_not_have_another_outputs_role():
    from scar_public.task_outcome import task_role
    m,c,task,text=scenario();task='Craft a club and obtain armor.'
    m.model.tasks=[task];m.model.known_tasks=[task];m.model.source_lines += ['[1] '+task,'I inspected club: Not armor.']
    assert task_role(m.model,'club',task)['status']=='TASK_NAMED_OUTPUT'
