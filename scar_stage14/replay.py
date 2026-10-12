"""Reuse deterministic action-prefix evidence, or schedule missing native suffixes."""
import datetime
from collections import defaultdict
from pathlib import Path
from scar.io import atomic_json,digest
from scar_stage14.common import ROOT,OLD,load,records,save_records,sha
from scar_stage14.executor import Executor


def verify_freezes():
    for f in ['parser_freeze.json','executor_freeze.json']:
        for p,h in load(ROOT/f)['hashes'].items():assert sha(p)==h,p
    for p,h in load(ROOT/'prior_manifest.json').items():assert sha(p)==h,p


def cache():
    out=defaultdict(dict)
    def add(sid,b,source):
        actions=[]
        for r in b['trace']:
            actions.append(r['action']);key=tuple(actions)
            if key in out[sid]:assert out[sid][key]['row']==r,(sid,key)
            else:out[sid][key]={'row':r,'source':source}
    for rec in records(OLD/'native_branches.jsonl.gz'):
        for cid,b in rec['branches'].items():add(rec['state_id'],b,{'stage':12,'candidate_id':cid})
    for rec in records('results/stage13/native_supplements.jsonl.gz'):
        add(rec['state_id'],rec['branch'],{'stage':13,'candidate_id':rec['candidate']['id'],'kind':rec['kind']})
    return out


def reuse(pub,intent,source):
    e=Executor(pub,intent);trace=[];provenance=[];prefix=[]
    while (action:=e.next()) is not None:
        prefix.append(action)
        if tuple(prefix) not in source:
            return None,{'matched_prefix':len(trace),'missing_public_action':action,'prefix':prefix}
        item=source[tuple(prefix)];r=item['row']
        assert r['before']==(trace[-1]['after'] if trace else pub['observation'])
        e.observe(action,r['before'],r['after']);trace.append(r);provenance.append(item['source'])
    return {'trace':trace,**e.result(),'provenance':provenance,'reused':True},None


def main():
    verify_freezes();assert not (ROOT/'replay_plan.json').exists()
    pubs=load(ROOT/'intent_public_inputs.json');existing=cache();reused=[];jobs=[]
    for row in load(ROOT/'candidate_intents.json'):
        sid=row['state_id'];i=row['intent'];b,missing=reuse(pubs[sid],i,existing[sid])
        if b is not None:reused.append({'state_id':sid,'intent_id':i['id'],'branch':b})
        else:jobs.append(dict(row,cache_gap=missing))
    save_records(ROOT/'reused_intent_branches.jsonl.gz',reused)
    atomic_json(ROOT/'replay_plan.json',{'jobs':jobs,'reused_intents':len(reused),
        'selection':'all missing deterministic prefixes, no native utility filtering','api_calls':0})
    atomic_json(ROOT/'replay_freeze.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'hashes':{str(p):sha(p) for p in [Path('scar_stage14/replay.py'),Path('scar_stage14/native.py'),ROOT/'replay_plan.json']}})
    print({'reused':len(reused),'new_native_intents':len(jobs)})

if __name__=='__main__':main()
