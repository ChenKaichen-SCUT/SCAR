"""Immutable first-run manifest; never overwrite an existing freeze."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from scar.io import atomic_json
from .config import ROOT, RESULTS, ENGINE, ENGINE_COMMIT, STAGE18_COMMIT, MODEL, METHODS, GAMES, SCHEDULE, EMBEDDING_PATH, EMBEDDING_REVISION
from .run import read, sha


def main():
    assert not (RESULTS/'freeze.json').exists()
    assert read(RESULTS/'preflight.json')['passed']
    assert read(RESULTS/'dependency_smoke.json')['passed']
    original = {p:h for p,h in read(ROOT/'results/stage18/freeze.json')['files'].items() if p.endswith('.py')}
    assert all(sha(ROOT/p)==h for p,h in original.items())
    actual = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ENGINE, text=True).strip()
    assert actual == ENGINE_COMMIT
    assert not subprocess.check_output(['git','status','--porcelain'], cwd=ENGINE, text=True).strip()
    engine_files = subprocess.check_output(['git','ls-files'],cwd=ENGINE,text=True).splitlines()
    engine_hashes = {p:sha(ENGINE/p) for p in engine_files if (ENGINE/p).is_file()}
    files = dict(original)
    for package in ('scar_stage18_fixed','scar_stage22'):
        for p in (ROOT/package).rglob('*.py'): files[str(p.relative_to(ROOT))] = sha(p)
    for p in ('preflight.json','dependency_smoke.json'):
        files['results/stage22/'+p] = sha(RESULTS/p)
    tracked = subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    prior = {p:sha(ROOT/p) for p in tracked if not p.startswith(('scar_stage22/','scar_stage18_fixed/','results/stage22/','reports/stage22/')) and (ROOT/p).is_file()}
    atomic_json(RESULTS/'prior_manifest.json',dict(files=prior))
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        stage18_original_commit=STAGE18_COMMIT, original_frozen_python_files=len(original),
        original_files_changed=[], engine_commit=actual, engine_files=engine_hashes,
        files=files, methods=METHODS, games=GAMES, schedule=SCHEDULE, model=MODEL,
        max_steps=300, P3_horizon=300, runs_per_combination=1, initial_seed=42,
        max_workers=12, reset_memory_each_game=True, previous_trajectories_as_input=False,
        hidden_knowledge_as_policy_input=False, follow_public_goal=True,
        goal_source='unchanged original PublicState regex and Controller.follow_public; no new quest parser',
        baselines='official classes and decision code unmodified',
        embedding=dict(model='Qwen/Qwen3-Embedding-0.6B', revision=EMBEDDING_REVISION, path=EMBEDDING_PATH),
        primary='unweighted mean raw main quest reward over three games',
        tiebreaker='unweighted mean raw sum of side_quest, exploration, craft, unique_kill',
        not_ttcl_ranking_reasons=['300 not 500 steps','DeepSeek Flash not approved Qwen backbone'],
        observation='official text/step; enable_obs_valid_actions=False',
        stop='official native done or 300 environment steps or recorded infrastructure failure',
        retries='429 transport rejection only; no paid parse resampling; no completed failure rerun')
    atomic_json(RESULTS/'freeze.json',manifest)
    print(json.dumps(dict(frozen=True,source_files=len(files),engine_files=len(engine_hashes),historical_files=len(prior))))


if __name__=='__main__': main()
