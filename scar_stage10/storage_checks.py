"""Zero-API capacity stress fixtures derived from one original Robot task.

These are component tests, not new task families or scored closed-loop episodes.
Fixture allocation changes are explicit. Rule code and original goal are intact;
all decisions use only real observations. Retrieval receives a named subgoal,
never an evaluator-written transfer/travel action.
"""
import argparse
import contextlib
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile

from scar.environment import restore, snapshot, state_digest, AGENT_ID
from scar.diagnostics.build import transition
from scar.io import atomic_json
from scar_stage10.controller import make_controller, restore_controller

OUT = Path('results/stage10')


def exercise(raw, case, spare, cache, wanted, missing=False):
    endings, results = [], []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            env = restore(raw, tmp); ctrl = make_controller('S3')
            for h in case['history']: ctrl.observe(h['before'], h['action'], h['after'])
            ctrl.set_goal(case['target_action'], case['public_goal'])
            trace = []
            def execute(action, purpose, setup=False):
                before = copy.deepcopy(env.obs[AGENT_ID]); state = copy.deepcopy(ctrl.to_dict())
                row = transition(env, action); ctrl.observe(before, action, row['after'])
                ctrl.table.observe(row['after'])
                trace.append(dict(purpose=purpose, setup=setup, controller_before=state,
                                  **row, controller_after=ctrl.to_dict(), physical_hash=state_digest(env)))
                return row
            execute('inspect inventory', 'public full-capacity disclosure', True)
            execute('inspect '+cache, 'public accessible-container disclosure', True)
            # Exercise the storage component with a specified blocked collection;
            # this is not a claim that the complete FIFO discovers this need.
            action, meta = ctrl.stash_option(f'store 2 {wanted} inventory')
            ctrl.selected_meta = meta; ctrl.storage_intent = copy.deepcopy(meta)
            assert action == f'take out {spare} inventory', action
            execute(action, 'controller releases one inventory slot without discarding')
            clone = restore_controller(json.loads(json.dumps(ctrl.to_dict())))
            assert clone.to_dict() == ctrl.to_dict()
            action = clone.choose(env.obs[AGENT_ID], 'wait'); ctrl = clone
            assert action == f'store 1 {spare} {cache}', action
            execute(action, 'controller finishes the single pending transfer')
            assert len(ctrl.stashes) == 1
            stash_state = copy.deepcopy(ctrl.stashes)
            # Component input now requests the additional stored copy. We test
            # retrieval correctness, not whether FIFO infers this future demand.
            original_location = ctrl.table.state['location']
            neighbor = ctrl.table.state['neighbors'][0]
            execute('enter '+neighbor, 'setup departure after storage', True)
            if missing:
                # Explicit exogenous-depletion fixture while the agent is away.
                # The controller learns only through the later native inspect.
                cid = env.world.auxiliary['obj_name_to_id'][cache]
                env.world.container_instances[cid].inventory.clear()
            action, meta = ctrl.retrieve(spare)
            assert action == 'enter '+original_location, action
            ctrl.selected_meta = meta; execute(action, 'controller follows historical location, not historical inventory')
            action, meta = ctrl.retrieve(spare)
            assert action == 'inspect '+cache, action
            ctrl.selected_meta = meta; execute(action, 'controller reconfirms contents using native inspection')
            action, meta = ctrl.retrieve(spare)
            if missing:
                assert action is None
                assert next(iter(ctrl.stashes.values()))['status'] == 'missing'
            else:
                assert action == f'take out {spare} {cache}', action
                ctrl.selected_meta = meta
                row = execute(action, 'controller retrieves confirmed stashed material')
                assert not row['semantic_rejection']
            endings.append(state_digest(env))
            results.append({'missing_variant': missing, 'trace': trace, 'record_after_store': stash_state,
                'exogenous_fixture_change': 'cached contents cleared while away' if missing else None,
                'final_records': ctrl.stashes, 'retrieval_action': action,
                'controller_actions_rejected': sum(r['semantic_rejection'] for r in trace if not r['setup']),
                'final_hash': endings[-1], 'passed': True})
    assert endings[0] == endings[1]
    return dict(results[0], independently_replayed_twice=True)


def main(runtime):
    root = Path(runtime); root.mkdir(parents=True, exist_ok=True)
    case = json.loads((OUT/'cases.json').read_text())[0]
    assert case['game'] == 'robot_kingdom' and case['cohort'] == 'development_old10'
    with (root/'storage_checks.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        raw = gzip.decompress((OUT/'initial_states'/f'{case["id"]}.pkl.gz').read_bytes())
        env = restore(raw, root); world, agent = env.world, env.agents[0]
        # Test-only allocation: same native bag definition, one spare empty
        # instance, and native wood planks filling the carried bag. No rule edit.
        spare_id = 'obj_wood_plank'; spare = world.objects[spare_id].name
        count = agent.inventory.capacity//world.objects[spare_id].size
        agent.inventory.items.clear(); agent.inventory.items[spare_id] = count
        cache = copy.deepcopy(world.container_instances[agent.inventory.container.id])
        cache.id = 'obj_small_bag_1'; cache.name = 'scout_satchel_1'; cache.inventory = {}
        world.objects[cache.id] = cache; world.container_instances[cache.id] = cache
        world.auxiliary['obj_name_to_id'][cache.name] = cache.id
        area = world.area_instances[env.curr_agents_state['area'][AGENT_ID]]
        area.objects[cache.id] = 1
        wanted = world.objects[next(oid for oid in area.objects if oid != cache.id and world.objects[oid].size is not None)].name
        transition(env, 'wait')  # Native refreshed public observation after setup.
        fixture = snapshot(env)
        path = OUT/'storage_fixture.pkl.gz'
        with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as f: f.write(fixture)
        records = [exercise(fixture, case, spare, cache.name, wanted, missing) for missing in [False, True]]
    result = {'case_id': case['id'], 'goal_unchanged': True, 'only_game': 'robot_kingdom', 'api_calls': 0,
        'fixture': {'path': str(path), 'serialized_sha256': hashlib.sha256(fixture).hexdigest(),
                    'allocations': {'filled_inventory_item': spare, 'amount': count, 'added_native_empty_container': cache.name}},
        'scope': 'capacity and stale-location component stress test; modified allocation, NOT new family or autonomous task success',
        'records': records, 'passed': all(r['passed'] and r['controller_actions_rejected'] == 0 for r in records)}
    atomic_json(OUT/'storage_checks.json', result); print(json.dumps({'passed': result['passed'], 'records': len(records)})); assert result['passed']


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); a = p.parse_args(); main(a.runtime)
