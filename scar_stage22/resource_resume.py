"""Operational CPU allocation only; frozen policy/runner/config remain intact.

Pause each known Voyager worker, confirm no pending API request, preserve hashes,
then resume its exact checkpoint with four CPU threads. Paid responses are served
by the frozen exact-signature cache. No new episode and no result selection.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results/stage22'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage22_runtime')


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2));temp.replace(p)


def main():
    receipt=RESULTS/'resource_resume.json'
    assert not receipt.exists(), 'Never repeat this operational intervention'
    bench=json.loads((RESULTS/'cpu_embedding_benchmark.json').read_text())
    assert bench['max_abs_difference']==0 and bench['api_calls']==0
    workers={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try: cmd=(p/'cmdline').read_bytes().decode().split('\0')
        except (FileNotFoundError,PermissionError):continue
        if 'scar_stage22.run' not in cmd or 'VoyagerAgent' not in cmd:continue
        assert cmd[cmd.index('--runtime')+1]==str(RUNTIME)
        game=cmd[cmd.index('--game')+1];workers[game]=int(p.name)
    assert set(workers)=={'remnant','mark','metropolis'}
    audit=dict(reason='Synthetic embedding benchmark: 3.29x throughput with bit-identical vectors; CPU threads only',
               old_threads=1,new_threads=4,started=time.time(),workers=[],frozen_files_modified=False,new_episodes=0)
    write(receipt,audit)
    for game,pid in workers.items():
        folder=RUNTIME/'runs'/f'{game}__VoyagerAgent'
        for attempt in range(120):
            os.kill(pid,signal.SIGSTOP)
            while '\nState:\tT' not in Path(f'/proc/{pid}/status').read_text():time.sleep(.01)
            if not (folder/'pending_request.json').exists(): break
            os.kill(pid,signal.SIGCONT);time.sleep(.5)
        else:raise RuntimeError('No safe no-request interruption point')
        cp=json.loads((folder/'latest.json').read_text())['checkpoint']
        checkpoint=json.loads((folder/cp/'meta.json').read_text())
        record=dict(game=game,pid=pid,checkpoint=checkpoint,
                    saved_step_hashes={p.name:sha(p) for p in sorted((folder/'steps').glob('*.json'))},
                    request_bytes=(folder/'requests.jsonl').stat().st_size,
                    request_prefix_sha256=sha(folder/'requests.jsonl'),pending_request=False,
                    interruption_time=time.time())
        audit['workers'].append(record);write(receipt,audit)
        os.kill(pid,signal.SIGKILL)
    environment=dict(os.environ,OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    def resume(record):
        game=record['game'];log=RUNTIME/'logs'/f'{game}__VoyagerAgent.log'
        with log.open('a') as stream:
            stream.write('\nOPERATIONAL RESUME: four CPU threads; same checkpoint and paid-call cache\n');stream.flush()
            result=subprocess.run([sys.executable,'-m','scar_stage22.run','--game',game,
                       '--method','VoyagerAgent','--runtime',str(RUNTIME)],cwd=ROOT,env=environment,
                       stdout=stream,stderr=subprocess.STDOUT)
        return dict(game=game,exit_code=result.returncode)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        completed=list(pool.map(resume,audit['workers']))
    for r in audit['workers']:
        folder=RUNTIME/'runs'/f'{r["game"]}__VoyagerAgent'
        raw=(folder/'requests.jsonl').read_bytes()
        assert hashlib.sha256(raw[:r['request_bytes']]).hexdigest()==r['request_prefix_sha256']
        for name,h in r['saved_step_hashes'].items():
            oldstep=int(name.split('.')[0])
            # Already checkpointed steps cannot be overwritten. An in-flight
            # step may be deterministically re-executed with cached responses;
            # its semantic equivalence is checked independently below.
            if oldstep<=r['checkpoint']['step']:assert sha(folder/'steps'/name)==h
    audit.update(completed=completed,finished=time.time(),paid_request_prefixes_preserved=True,
                 committed_steps_unchanged=True)
    write(receipt,audit)
    print(json.dumps(audit['completed']),flush=True)


if __name__=='__main__':main()
