from scar_public.task_progress import (ProgressMemory, ProgressController, update_obligations,
                                       exploration_options, context_key)


def test_reminder_preserves_task_but_explicit_replacement_does_not():
    tasks = {}; events = []
    update_obligations(tasks, 'guide says: Craft any armor.', 0, events)
    update_obligations(tasks, 'guide says: "You seem stuck. Talk to me if you need a reminder of your current task."', 1, events)
    assert tasks['guide']['quote'] == 'Craft any armor.'
    update_obligations(tasks, 'guide says: Search the hills for a shrine.', 2, events)
    assert tasks['guide']['quote'] == 'Search the hills for a shrine.'
    assert events[-1]['completion_inferred'] is False


def test_multiline_task_retains_region_evidence_and_exact_instruction():
    tasks = {}; events = []
    update_obligations(tasks, 'guide says: The shrine is somewhere within:\n  Valley, hills; Marsh, bog\nSearch the named regions until the shrine appears.\n\nI am holding no objects.', 1, events)
    assert tasks['guide']['quote'] == 'Search the named regions until the shrine appears.'
    assert 'Marsh, bog' in tasks['guide']['block']
    assert 'I am holding' not in tasks['guide']['block']


def test_stage_completion_retires_only_explicit_next_contact():
    tasks = {}; events = []
    update_obligations(tasks, 'a says: Find a shrine.\n\nb says: Craft a key.', 0, events)
    update_obligations(tasks, 'Stage completed. It glows.\nTalk to a about what to do next.', 1, events)
    assert 'a' not in tasks and 'b' in tasks


def scenario():
    m = ProgressMemory(); m.progress_mode='execute'; c = ProgressController(m)
    goal = 'Search the regions until the shrine appears.'
    text = 'Current Time: 0001-01-01 10:00:00\nCurrent Location: Castle, hall\nI am holding no objects.\nI have equipped no objects.\nI see no objects near me.\nMy health is at 100.\nNeighboring areas: library.'
    m.prompt(text + '\n\nguide says: ' + goal); m.refresh_tasks()
    m.frame = dict(goal_quote=goal, method='Search', assessment='Unknown', expected='New region')
    m.model.locations['Castle, library'] = dict(objects={}, neighbors=['hall', 'bog'])
    m.model.edges = {'Castle, hall': {'library':'Castle, library'}, 'Castle, library': {'hall':'Castle, hall'}}
    return m, c, goal, text


def test_frontier_plan_uses_known_transit_and_does_not_invent_destination():
    m, c, goal, text = scenario()
    result = exploration_options(m.model, goal, {}, context_key(m.model, text))
    assert result[0]['plan'] == ['enter library', 'enter bog']
    assert result[0]['frontier_location'] == 'Castle, library'
    assert 'destination' not in result[0]


def test_search_executes_frontier_program_without_extra_model_query():
    m, c, goal, text = scenario()
    result = c.navigation(text, 10, dict(action='wait', frame=m.frame))
    assert result['action'] == 'enter library' and m.progress_pending
    assert c.navigation(text.replace('100.', '10.'), 11) is None


def test_never_overrides_healing_fighting_or_object_collection():
    m, c, goal, text = scenario()
    for action in ('eat bread', 'attack enemy', 'pick up shrine', 'talk to guide'):
        assert c.navigation(text, 10, dict(action=action, frame=m.frame)) is None


def test_observe_mode_records_choice_without_execution_or_pending_state():
    m, c, goal, text = scenario(); m.progress_mode = 'observe'
    assert c.navigation(text, 10, dict(action='wait', frame=m.frame)) is None
    assert m.progress_decisions and not m.progress_pending and not m.progress_program


def test_unknown_locked_exit_is_not_presented_as_a_new_frontier():
    m, c, goal, text = scenario()
    m.model.blocked_routes.append(dict(location='Castle, library', action='bog', step=0, holding={}, equipped={}))
    assert exploration_options(m.model, goal, {}, context_key(m.model, text)) == []


def test_non_task_dialogue_does_not_cancel_active_instruction():
    tasks = {}; events = []
    update_obligations(tasks, 'guide says: Craft any armor.', 0, events)
    update_obligations(tasks, 'guide says: I live in this town.', 1, events)
    assert tasks['guide']['quote'] == 'Craft any armor.'


def test_checkpoint_migration_reconstructs_obligations_and_preserves_new_state():
    m, c, goal, text = scenario(); state=m.state(); state.pop('progress_tasks'); state.pop('progress_observed')
    n=ProgressMemory(); n.load(state)
    assert n.progress_tasks['guide']['quote']==goal
    n.progress_attempts['edge']='context'; other=ProgressMemory(); other.load(n.state())
    assert other.progress_attempts==n.progress_attempts


def test_old_inactive_quotes_cannot_be_rebound_by_actor():
    m, c, goal, text = scenario()
    update_obligations(m.progress_tasks, 'guide says: Craft a sword.', 1, m.progress_events)
    c.bind(goal)
    assert goal not in c.view().tasks


def test_partial_stage_completion_does_not_retire_main_goal():
    tasks = {}; events = []
    update_obligations(tasks, 'guide says: Main goal: Investigate the district and recover the cipher.', 0, events)
    update_obligations(tasks, 'guide says: Obtain a weapon.', 1, events)
    update_obligations(tasks, 'Stage completed: Obtain a weapon.\nTalk to guide about what to do next.', 2, events)
    assert 'guide' not in tasks and tasks['guide:main']['quote'].startswith('Investigate')
    update_obligations(tasks, 'guide says: Main goal: Explore the final vault.', 3, events)
    assert tasks['guide:main']['quote']=='Explore the final vault.'


def test_reinspection_timestamp_is_not_new_information():
    from scar_public.task_progress import probe_content_key
    m,c,goal,text=scenario(); focus=dict(task=goal,target='paper')
    m.model.current['holding']={'paper_0':1}; m.model.documents['paper_0']=dict(text='',observed_at=0)
    before=probe_content_key(m.model,focus,'paper_0')
    m.model.documents['paper_0']['observed_at']=200
    assert probe_content_key(m.model,focus,'paper_0')==before
    first=c.bounded_probe(focus,text,10); assert first['action']=='inspect paper_0'
    m.model.documents['paper_0']['observed_at']=201
    assert c.bounded_probe(focus,text,11) is None
    m.model.documents['paper_0']['text']='new task content'
    assert c.bounded_probe(focus,text,12)['action']=='inspect paper_0'


def test_probe_records_observed_content_to_prevent_immediate_reinspection():
    m,c,goal,text=scenario(); focus=dict(task=goal,target='paper')
    m.model.current['holding']={'paper_0':1}
    first=c.bounded_probe(focus,text,10); m.last_action=first['action']
    m.model.documents['paper_0']=dict(text='',observed_at=11)
    c.prepare_decision(text,11)
    assert c.bounded_probe(focus,text,11) is None
