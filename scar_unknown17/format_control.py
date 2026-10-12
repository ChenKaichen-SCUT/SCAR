"""Additional matched memory-format control, independently frozen before calls.

The original STMFacts retains the execution-only memory format inherited from
StructuredAgent. This differs from official STM retaining model reasoning. Do
not change or rerun frozen methods: add a same-format no-summary comparator.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import contextlib
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
from functools import lru_cache
from scar.io import atomic_json,digest
from scar_unknown17.agent import UnknownAgent
from scar_unknown17.run import episode,make_tasks
from scar_sequence.prepare import NoAPIProvider


@lru_cache(None)
def agent_class(base):
    return type('UnknownSTMFormatControl__'+base.__name__,(UnknownAgent,base),
        {'options':(False,'none',False,False),'__module__':base.__module__})


def make_agent(algorithm,game,provider,settings,memory_dir):
    assert algorithm=='STMFormatControl'
    from scar.integration import DeepSeekMemoryConfig
    from utils import dynamic_load_game_class
    cfg=DeepSeekMemoryConfig(llm_name=settings['model'],llm_provider='deepseek',embed_name=settings['embedding_model'],
        max_new_tokens=settings['max_tokens'],temperature=settings['temperature'],short_term_memory_size=5,
        torch_seed=settings.get('seed',42),full_mem_path=str(memory_dir))
    cfg.scar_provider=provider
    return agent_class(dynamic_load_game_class(game,'agent','Agent'))('agent_adam_davis','adam_davis',cfg)


def run_control(job):
    task,config,runtime,key,smoke=job
    import scar_unknown17.agent as factory
    old=factory.make_agent;factory.make_agent=make_agent
    try:return episode(task,config,runtime,key,4,provider_factory=NoAPIProvider if smoke else None)
    finally:factory.make_agent=old


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--freeze-only',action='store_true')
    p.add_argument('--key',default='/root/.scar-deepseek-key');a=p.parse_args();root=Path(a.runtime);out=Path('results/unknown17')
    config=json.loads(Path('configs/protocol_unknown17.json').read_text());config=dict(config,algorithms=['STMFormatControl'],protocol_cohort='unknown17_format_control_v1')
    cs=json.loads((out/'cases.json').read_text());tasks=make_tasks(config,cs)
    for t in tasks:t['initial_snapshot']=str(root/'initials'/f'{t["id"]}.pkl')
    path=out/'format_control_freeze.json'
    if a.freeze_only:
        if path.exists():raise ValueError('Already frozen')
        smoke=dict(tasks[0],task_id='smoke-format-control',max_steps=2)
        result=run_control((smoke,config,str(root/'integration_final'),None,True))
        assert result['status']=='completed' and result['api_calls']==0
        atomic_json(path,{'config':config,'dataset_digest':digest(cs),'episodes':17,
            'code_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'reason':'STMFacts changes execution-memory format relative to official STM. Add same-format no-summary comparator without touching frozen methods.',
            'decision_basis':'code inspection, not formal outcome scores','shared_total_guard_usd':4,
            'smoke':{k:result[k] for k in ['status','steps','api_calls','cost_usd']},
            'additional_cost_estimate_usd':17*40*.0005,'new_api_calls_so_far_for_control':0})
        print(json.dumps({'control_frozen':True,'episodes':17,'shared_cap':4}));return
    frozen=json.loads(path.read_text());assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==frozen['code_hash']
    assert digest(cs)==frozen['dataset_digest'] and config==frozen['config']
    atomic_json(root/'format_control_tasks.json',tasks)
    with ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('spawn')) as pool:
        for r in pool.map(run_control,[(t,config,str(root),a.key,False) for t in tasks]):
            print(json.dumps({k:r.get(k) for k in ['task_id','status','steps','cost_usd','error']}),flush=True)
    # Preserve original task manifest; all_tasks is only the evaluation manifest.
    atomic_json(root/'all_tasks.json',json.loads((root/'tasks.json').read_text())+tasks)

if __name__=='__main__':main()
