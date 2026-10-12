"""Preserve and classify algorithmic aborts; never rerun a paid episode.

The frozen runner labels generic exceptions 'failed'. A reproducible exception in
policy.choose is a method failure, not a transient infrastructure problem. Keep
raw summaries/statuses unchanged and publish the evaluation adjudication.
"""
import argparse
import copy
import gzip
import json
from pathlib import Path
import traceback
from scar.environment import restore,AGENT_ID,state_digest
from scar.io import atomic_json,read_jsonl
from scar_unknown17.audit import branch
from scar_unknown17_stage7.controller import Stage7Controller,FLAGS
from scar_unknown17_stage7.offline import save_state


def adjudicated_status(task_id,raw_status):
    path=Path('results/stage7/method_terminations.json')
    if not path.exists():return raw_status
    for r in json.loads(path.read_text())['terminations']:
        if r['task_id']==task_id and r['reproduced'] and r['classification']=='method_abort':return 'method_abort'
    return raw_status


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime);out=Path('results/stage7');records=[]
    for task in json.loads((root/'tasks.json').read_text()):
        folder=root/'runs'/task['task_id'];status=json.loads((folder/'status.json').read_text())
        if status['status']!='failed':continue
        error=(folder/'error.txt').read_text()
        if 'RecursionError' not in error or 'scar_unknown17_stage7/controller.py' not in error:
            raise RuntimeError('Unclassified failure cannot be silently counted as method abort: '+task['task_id'])
        last=sorted((folder/'steps').glob('*/checkpoint.json'))[-1].parent
        memory=json.loads((last/'memory/unknown.json').read_text());raw=(last/'environment.pkl').read_bytes();env=restore(raw)
        request=read_jsonl(folder/'requests.jsonl')[-1]
        proposal=json.loads(request['raw_response']['choices'][0]['message']['content'])['action']
        checks=[]
        for _ in range(2):
            c=Stage7Controller.from_dict(memory['controller'])
            try:action=c.choose(env.obs[AGENT_ID],proposal);result={'error':None,'action':action}
            except Exception as exc:result={'error':type(exc).__name__,'message':str(exc)}
            checks.append(result)
        variants=[]
        for flag in FLAGS:
            c=Stage7Controller.from_dict(memory['controller']);c.flags[flag]=not c.flags[flag]
            try:action=c.choose(env.obs[AGENT_ID],proposal);result={'error':None,'action':action}
            except Exception as exc:result={'error':type(exc).__name__,'message':str(exc)}
            variants.append({'flag':flag,**result})
        trace=out/'method_errors'/f'{task["task_id"]}.txt.gz';trace.parent.mkdir(exist_ok=True)
        with gzip.open(trace,'wt') as f:f.write(error)
        records.append({'task_id':task['task_id'],'case_id':task['id'],'algorithm':task['algorithm'],
            'raw_status':status,'raw_summary':json.loads((folder/'summary.json').read_text()),
            'classification':'method_abort','reproduced':all(r['error']=='RecursionError' for r in checks),
            'committed_actions':len(list((folder/'steps').glob('*/checkpoint.json'))),'base_proposal_at_abort':proposal,
            'request_id':request['request_id'],'paid_request_at_abort_usd':request['cost_usd'],
            'checkpoint':save_state(raw,'abort-'+task['task_id']),'public_observation':env.obs[AGENT_ID],
            'controller_before_abort':memory['controller'],'original_reproductions':checks,'one_switch_alternatives':variants,
            'base_proposal_effect':branch(raw,[proposal],task),
            'non_aborting_toggle_effects':[{'flag':v['flag'],'effect':branch(raw,[v['action']],task)} for v in variants if v['error'] is None],
            'trace_path':str(trace),'cause':'_station -> _explore -> _gap_explore -> same product _station recursion when station route unavailable',
            'scoring':'failure in full17 denominator; raw failed status preserved; no further API call, no repair of frozen policy, no paid rerun',
            'followup_limit':'26 actions observed if this checkpoint has26; remaining40 delay penalty is not actually observed followup'})
    result={'terminations':records,'api_calls':0,'raw_runtime_files_changed':False,
        'passed':all(r['reproduced'] for r in records)}
    atomic_json(out/'method_terminations.json',result);assert result['passed']
    print(json.dumps({'method_aborts':len(records),'zero_API_reproduction_passed':result['passed']}))

if __name__=='__main__':main()
