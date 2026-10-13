"""Same official reset/act/step/update_scores interface, with exact checkpoints."""
import argparse
import contextlib
import copy
import gzip
import json
import os
import random
import shutil
import time
import traceback
from pathlib import Path
import numpy as np
from scar.io import atomic_json, append_jsonl, digest
from scar.environment import create_environment, snapshot, restore, state_digest
from .config import ROOT, RESULTS, ENGINE, MODEL, MAX_STEPS, AGENT_ID, SEED, METHODS, GAMES
from .integration import make_agent
from .provider import Provider


def read(path): return json.loads(Path(path).read_text())


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_freeze():
    freeze = read(RESULTS / 'freeze.json')
    for name, value in freeze['files'].items():
        assert sha(ROOT / name) == value, 'Frozen file changed: ' + name
    for name, value in freeze['engine_files'].items():
        assert sha(ENGINE / name) == value, 'Official engine changed: ' + name
    return freeze


def gzip_json(path, rows):
    with gzip.open(path, 'wt', encoding='utf-8') as stream:
        for row in rows: stream.write(json.dumps(row, ensure_ascii=False) + '\n')


def checkpoint(folder, env, agent):
    step = env.steps
    dest, temp = folder / f'checkpoint-{step:03d}', folder / f'.checkpoint-{step:03d}'
    if temp.exists(): shutil.rmtree(temp)
    temp.mkdir()
    if hasattr(agent, 'save_memory'): agent.save_memory(str(temp))
    (temp / 'physical.pkl').write_bytes(snapshot(env))
    atomic_json(temp / 'meta.json', dict(step=step, state_hash=state_digest(env)))
    temp.rename(dest)
    atomic_json(folder / 'latest.json', dict(checkpoint=dest.name))
    for other in folder.glob('checkpoint-*'):
        if other != dest: shutil.rmtree(other)


def archive(folder, output, summary):
    output.mkdir(parents=True, exist_ok=True)
    rows = [read(p) for p in sorted((folder / 'steps').glob('*.json'))]
    requests = [json.loads(line) for line in (folder / 'requests.jsonl').read_text().splitlines()] if (folder / 'requests.jsonl').exists() else []
    gzip_json(output / 'trajectory.jsonl.gz', rows)
    gzip_json(output / 'requests.jsonl.gz', requests)
    summary.update(steps=len(rows), requests=len(requests),
                   input_tokens=sum(r.get('usage', {}).get('prompt_tokens', 0) for r in requests),
                   output_tokens=sum(r.get('usage', {}).get('completion_tokens', 0) for r in requests),
                   cost_usd=sum(r.get('cost_usd', 0) for r in requests),
                   charged_or_reserved_usd=sum(r['charged_or_reserved_usd'] for r in requests),
                   invalid_actions=sum(r['invalid_action'] for r in rows))
    if rows:
        summary.update(scores=rows[-1]['scores'], final_state_hash=rows[-1]['state_hash'], done=rows[-1]['done'])
    for name in ('config.json', 'initial_public.json', 'run_config.json'):
        source = folder / name
        if source.exists(): shutil.copyfile(source, output / name)
    if (folder / 'voyager_debug.txt').exists():
        with gzip.open(output / 'voyager_debug.txt.gz', 'wb') as stream:
            stream.write((folder / 'voyager_debug.txt').read_bytes())
    atomic_json(output / 'summary.json', summary)


def execute(game, method, runtime, key):
    folder = Path(runtime) / 'runs' / f'{game}__{method}'
    output = RESULTS / 'runs' / folder.name
    if (output / 'summary.json').exists(): return read(output / 'summary.json')
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'steps').mkdir(exist_ok=True)
    (folder / 'memory').mkdir(exist_ok=True)
    metadata = folder / 'run_config.json'
    if not metadata.exists():
        atomic_json(metadata, dict(game=game, method=method, seed=SEED, max_steps=MAX_STEPS,
                    model=MODEL, started=time.time(), initial_history=[], memory_reset=True,
                    enable_obs_valid_actions=False, protocol='300-step non-ranking research experiment'))
    meta = read(metadata)
    summary = dict(meta, status='infrastructure_error', error=None)
    env = None
    try:
        provider = Provider(folder, runtime, key)
        random.seed(SEED); np.random.seed(SEED)
        agent = make_agent(method, game, provider, folder / 'memory')
        if (folder / 'latest.json').exists():
            cp = folder / read(folder / 'latest.json')['checkpoint']
            if hasattr(agent, 'load_memory'): agent.load_memory(str(cp))
            env = restore(cp / 'physical.pkl', folder, agent)
            assert state_digest(env) == read(cp / 'meta.json')['state_hash']
        else:
            env, obs = create_environment(game, SEED, folder / 'initial', agent, ENGINE)
            env.config_path = str(folder / 'config.json')
            env.run_dir = str(folder)
            env.config.update(game_name=game, seed=SEED, max_steps=MAX_STEPS,
                              agent=method, llm_name=MODEL['model'], stage22_research_only=True)
            env.update_config()
            atomic_json(folder / 'initial_public.json', dict(observation=obs[AGENT_ID],
                        initial_state_hash=state_digest(env), seed=SEED, previous_history=[]))
            if method == 'Stage18-Fixed': agent.initialize_official(obs[AGENT_ID])
            checkpoint(folder, env, agent)
        initial = read(folder / 'initial_public.json')
        summary['initial_state_hash'] = initial['initial_state_hash']
        while env.steps < MAX_STEPS:
            if env.steps and read(folder / 'steps' / f'{env.steps:03d}.json')['done']: break
            step = env.steps + 1
            before = copy.deepcopy(env.obs[AGENT_ID])
            before_hash = state_digest(env)
            provider.begin_step(step)
            started = time.time()
            action, tin, tout, response = agent.act(before)
            decision_time = time.time() - started
            audit = copy.deepcopy(agent.decision) if method == 'Stage18-Fixed' else None
            # This is the official evaluation loop. Death alone does not add an
            # unofficial early-stop condition; native done controls termination.
            observations, rewards, done, info = env.step({AGENT_ID: action})
            env.update_scores(rewards)
            after = copy.deepcopy(observations[AGENT_ID])
            row = dict(step=step, official_zero_based_log_step=step-1, game=game, method=method,
                       observation=before, action=action, response=response, feedback=after,
                       reward=copy.deepcopy(vars(rewards[AGENT_ID])), scores=copy.deepcopy(env.scores[AGENT_ID]),
                       done=bool(done), info=info,
                       invalid_action=bool(info.get('step_invalid_action', {}).get(AGENT_ID, False)),
                       agent_return_input_tokens=tin, agent_return_output_tokens=tout,
                       decision_time=decision_time, state_hash_before=before_hash,
                       state_hash=state_digest(env), decision=audit,
                       main_quest_progress=copy.deepcopy(env.curr_agents_state.get('main_quest_progress', {}).get(AGENT_ID)),
                       recorded_at=time.time())
            # Persist the native action before ingestion so a logging/controller
            # fault cannot silently erase an already-executed action.
            atomic_json(folder / 'steps' / f'{step:03d}.json', row)
            env.update_config()
            if hasattr(agent, 'observe_transition'): agent.observe_transition(before, action, after)
            checkpoint(folder, env, agent)
            atomic_json(folder / 'progress.json', dict(step=step, scores=row['scores'],
                        cost_usd=provider.episode.total(), updated=time.time()))
            if done: break
        summary['status'] = 'native_done' if env.steps and read(folder / 'steps' / f'{env.steps:03d}.json')['done'] else 'step_limit'
        if hasattr(agent, 'save_memory'): agent.save_memory(str(folder / 'memory'))
        env.update_config()
    except Exception as exc:
        summary.update(error=dict(type=type(exc).__name__, message=str(exc)), traceback=traceback.format_exc())
        print(summary['traceback'], flush=True)
    summary.update(finished=time.time(), elapsed_seconds=time.time()-meta['started'])
    archive(folder, output, summary)
    return read(output / 'summary.json')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', choices=GAMES, required=True)
    parser.add_argument('--method', choices=METHODS, required=True)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--key', default=str(ROOT.parent / 'miyao.txt'))
    args = parser.parse_args()
    check_freeze()
    print(json.dumps(execute(args.game, args.method, args.runtime, args.key), ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
