"""Final local artifact/credential checks; never starts an experiment."""
import gzip
import hashlib
import importlib.metadata
import json
import platform
import re
from pathlib import Path
from .config import ROOT,RESULTS,REPORTS,GAMES,METHODS
from .analyze import read,write


def main():
    verification=read(RESULTS/'verification.json')
    assert verification['passed'] and verification['runs']==15 and verification['actions']==4500
    stats=read(RESULTS/'per_run.json')
    assert len(stats)==15 and all(s['steps']==300 and s['status']=='step_limit' for s in stats)
    assert not any(s['main_quest_complete'] for s in stats)
    assert sum(s['requests'] for s in stats)==verification['requests']==5666
    assert abs(sum(s['cost_usd'] for s in stats)-verification['cost_usd'])<1e-9
    resume=read(RESULTS/'resource_resume.json')
    assert resume['paid_request_prefixes_preserved'] and resume['committed_steps_unchanged']
    for g in GAMES:
        for m in METHODS:
            p=RESULTS/'runs'/f'{g}__{m}'
            for n in ('trajectory.jsonl.gz','requests.jsonl.gz','config.json','initial_public.json','run_config.json','summary.json','native_prebootstrap_config.json.gz'):
                assert (p/n).is_file(),(g,m,n)
            assert list((p/'final_memory').glob('*.gz')) or m=='NoMemoryAgent'
    required=['README.md','工程修复与算法差异审计.md','官方评测协议核验.md','复现与运行事件记录.md',
              '三游戏五算法主结果表.md','控制器贡献与失败诊断.md','模型调用与解析异常.md','300步实验科研总结.md']
    required += [g+'_逐游戏案例.md' for g in GAMES]
    assert all((REPORTS/n).is_file() for n in required)
    # The passing top-level receipt refers to record/source integrity, not all
    # native replays. Preserve partial replay failures explicitly.
    verification['passed_scope']='Frozen source, original record, score and usage integrity; native replay completeness is reported separately'
    write(RESULTS/'verification.json',verification)
    packages={}
    for name in ('numpy','torch','transformers','huggingface_hub','openai','matplotlib','cloudpickle','pytest'):
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    write(RESULTS/'analysis_environment.json',dict(python=platform.python_version(),packages=packages,api_calls=0))
    write(RESULTS/'execution_completion.json',dict(completed=15,expected=15,actions=4500,requests=verification['requests'],
        cost_usd=verification['cost_usd'],all_step_limit=True,full_main_quest_completions=0,
        new_episodes_after_freeze=15,completed_game_reruns=0,resource_resumed_existing_episodes=3,
        raw_dispatch_note='batch_completion.json records termination of 3 old Voyager workers; resource_resume.json proves their original committed prefixes preserved. Each has exactly one final 300-action summary.',
        research_verdict='NO-GO',ranking_eligible=False))
    files=[]
    for folder in (RESULTS,REPORTS,ROOT/'scar_stage22',ROOT/'scar_stage18_fixed',ROOT/'tests'):
        for p in folder.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:continue
            if folder==ROOT/'tests' and 'stage22' not in p.name:continue
            if p.name in ('artifact_manifest.json','delivery_check.json'):continue
            files.append(p)
    private=ROOT.parent/'miyao.txt';secret=None
    if private.exists():
        from scar.providers.deepseek import read_key
        secret=read_key(private).encode()
    for p in files:
        raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
        assert not secret or secret not in raw, 'Private credential found: '+str(p.relative_to(ROOT))
        assert not re.search(rb'-----BEGIN (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY-----',raw)
        assert p.stat().st_size<95_000_000, 'GitHub single-file size bound'
    write(RESULTS/'artifact_manifest.json',dict(files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))},
        scope='Stage22 delivered source, reports and results; excludes this manifest and delivery receipt',api_calls=0))
    write(RESULTS/'delivery_check.json',dict(passed=True,runs=15,report_files=len(required),
        checked_files=len(set(files)),specific_private_credential_checked=secret is not None,
        private_credentials_found=False,api_calls=0,native_replay_all_passed=verification['native_replay_all_passed'],
        publication_contents='Implemented source and experiment/analysis artifacts only; no downloaded engine, generator or embedding weights'))
    print(json.dumps(read(RESULTS/'delivery_check.json')))


if __name__=='__main__':main()
