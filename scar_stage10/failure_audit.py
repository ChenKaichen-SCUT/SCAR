"""Preserve all method aborts; classify model-format versus controller failures."""
import argparse,gzip,json
from pathlib import Path
from scar.io import atomic_json,read_jsonl

def main(runtime):
    root=Path(runtime);out=Path('results/stage10');records=[]
    for task in json.loads((root/'tasks.json').read_text()):
        folder=root/'runs'/task['task_id'];p=folder/'status.json'
        if not p.exists():continue
        status=json.loads(p.read_text())
        if status['status'] not in {'method_abort','failed','worker_failed'}:continue
        error=status.get('error','');trace=(folder/'error.txt').read_text() if (folder/'error.txt').exists() else ''
        name='controller_recursion' if 'RecursionError' in error else 'model_response_format' if 'ModelResponseError' in error else 'other_execution_error'
        req=read_jsonl(folder/'requests.jsonl');steps=sorted((folder/'steps').glob('*/checkpoint.json'))
        path=out/'method_errors'/f'{task["task_id"]}.txt.gz';path.parent.mkdir(exist_ok=True)
        with gzip.open(path,'wt') as f:f.write(trace)
        records.append({'task_id':task['task_id'],'case_id':task['id'],'method':task['algorithm'],'raw_status':status,
            'classification':name,'committed_actions':len(steps),'trace_path':str(path),
            'last_requests':[{k:r.get(k) for k in ['request_id','status','cost_usd','usage','error']} for r in req[-3:]],
            'last_controller_checkpoint':json.loads((steps[-1].parent/'memory/unknown.json').read_text()) if steps else None,
            'policy_changed':False,'paid_retry_episode':False,
            'scoring':'method abort included as failure; requests beyond committed actions charged; no invented environment transition'})
    atomic_json(out/'method_terminations.json',{'records':records,'API_calls':0,'raw_runtime_changed':False})
    print(json.dumps({'terminations':len(records),'kinds':[r['classification'] for r in records]}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();main(a.runtime)
