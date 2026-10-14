"""Offline descriptive statistics, full timelines and exact-source evidence index."""
import csv
import re
from collections import Counter
from functools import lru_cache
from agents.agc.state import extract
from scar_stage28.chain import directed
from .common import *

VARIANTS=['OriginalRecovery','OracleGoalStack','UnpromptedReference']

@lru_cache(None)
def data(ident,variant):
    s=selected()[ident]
    source=(ROOT/s['source_trajectory'] if variant=='UnpromptedReference' else
            ROOT/f'results/stage28/runs/{ident}/OracleRecovery/trajectory.jsonl.gz' if variant=='OriginalRecovery' else
            RESULTS/f'runs/{ident}/OracleGoalStack/trajectory.jsonl.gz')
    original=rows(source);rr=[r for r in original if r['step']>s['step']]
    qq=[q for q in rows(source.parent/'requests.jsonl.gz') if q['step']>s['step']]
    return s,rr,qq,source,{r['step']:i for i,r in enumerate(original,1)}

def accepted(r):
    x=extract(r['feedback'])
    return not x['failed'] and not re.search(r'^Failed to\b',x['feedback'],re.I) and not r['info'].get('step_invalid_action',{}).get(AGENT_ID,False)

def chapter(r):return int((r.get('main_quest_progress') or {}).get('chapter',0))>=1

def measure(s,rr,prefix,horizon):
    observed=rr[:horizon]
    prior=[extract(r[k]) for r in prefix for k in ['observation','feedback']]
    seen={x['signature'] for x in prior};locations={x['location'] for x in prior}
    novel=[];areas=[];holding=[];repairs=[];success=[];repeat=[];state_loss=[]
    for r in observed:
        before=extract(r['observation']);after=extract(r['feedback']);ok=accepted(r)
        if after['signature'] not in seen:novel.append(r['step'])
        if after['location'] not in locations:areas.append(dict(step=r['step'],location=after['location']))
        seen.add(after['signature']);locations.add(after['location'])
        # Darkness/unknown holdings must not create an artificial resource gain/loss.
        if before['hands'] is not None and after['hands'] is not None:
            b=Counter(before['hands'])+Counter(before['equipment'] or {})
            a=Counter(after['hands'])+Counter(after['equipment'] or {})
            if a-b:holding.append(dict(step=r['step'],items=dict(a-b)))
            if b-a:state_loss.append(dict(step=r['step'],items=dict(b-a),action=r['action']))
        if ok and directed(s,r)['recovery_directed']:repairs.append(r['step'])
        if r['action']==s['candidate_action']:(success if ok else repeat).append(r['step'])
    n=len(observed)
    return dict(horizon=horizon,actions=n,window_complete=n==horizon,accepted=sum(bool(accepted(r)) for r in observed),
        rejected=sum(not accepted(r) for r in observed),wait=sum(r['action']=='wait' for r in observed),
        successful_original_retry=bool(success),successful_original_retry_steps=success,repeated_original_rejection_steps=repeat,
        stopped_original_repetition=not repeat,recovery_execution_steps=repairs,
        new_public_state_steps=novel,new_location_events=areas,holding_increases=holding,holding_decreases=state_loss,
        main_gain=sum(r['reward']['quest'] for r in observed),main_final=observed[-1]['scores']['quest'] if observed else None,
        chapter1=chapter(observed[-1]) if observed else False,
        deaths=sum(r['reward']['death'] for r in observed),craft_rewards=sum(r['reward']['craft'] for r in observed))

def counts(pairs,metric,window='20'):
    c=Counter(both=0,OriginalRecovery_only=0,OracleGoalStack_only=0,neither=0)
    for p in pairs:
        a=bool(p['variants']['OriginalRecovery']['windows'][window][metric]);b=bool(p['variants']['OracleGoalStack']['windows'][window][metric])
        c['both' if a and b else 'OriginalRecovery_only' if a else 'OracleGoalStack_only' if b else 'neither']+=1
    return dict(c)

def save(p,text):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n')

def main():
    offline();assert read(RESULTS/'completion.json')['complete']
    pairs=[];audit=[];accounting=[];exceptions=[]
    for ident in CASES:
        s=selected()[ident];prefix=json.loads(gzip.decompress((ROOT/f'results/stage27/checkpoints/{ident}/public_prefix.json.gz').read_bytes()))
        p=dict(id=ident,failure_step=s['step'],failed_action=s['candidate_action'],original_goal=s['current_goal'],type=s['failure_type'],variants={})
        for variant in VARIANTS:
            _,rr,qq,path,lines=data(ident,variant)
            p['variants'][variant]=dict(source=str(path.relative_to(ROOT)),actions=len(rr),first_action=rr[0]['action'],
                windows={str(w):measure(s,rr,prefix,w) for w in [5,20]},full=measure(s,rr,prefix,len(rr)),
                requests=len(qq),tokens_in=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),
                tokens_out=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),cost_usd=sum(q.get('cost_usd',0) for q in qq),
                common_peak_rate_reference_usd=sum(q.get('peak_rate_reference_cost_usd',0) for q in qq),
                charged_this_stage=variant=='OracleGoalStack')
            if variant=='UnpromptedReference':continue
            source_hash=sha(path)
            text=[f'# {ident} / {variant}',f'原目标：{s["current_goal"]}；原失败动作：`{s["candidate_action"]}`。\n',
                  '步骤均为绝对动作号；来源及请求 ID 见 evidence_index.jsonl.gz。']
            for r in rr:
                prop=r['decision']['attempts'][-1]['proposal'];before=extract(r['observation']);after=extract(r['feedback'])
                entry=dict(id=ident,variant=variant,step=r['step'],continuation_step=r['step']-s['step'],source=str(path.relative_to(ROOT)),line=lines[r['step']],
                    action=r['action'],accepted=bool(accepted(r)),goal=prop.get('goal_description'),reasoning=prop.get('reasoning'),
                    goal_evidence=prop.get('goal_evidence'),control_goal=r['control_after']['goal'],
                    public_feedback=after['feedback'],location=after['location'],hands=after['hands'],ground=after['ground'],
                    scores=r['scores'],reward=r['reward'],state_hash=r['state_hash'],
                    request_ids=[q['request_id'] for q in qq if q['step']==r['step']],
                    action_overridden=r.get('action_overridden',False),source_sha256=source_hash)
                audit.append(entry)
                text += [f'\n## 动作 {r["step"]}: {r["action"]}',f'目标：{prop.get("goal_description")}；状态：{r["control_after"]["goal"].get("status")}；接受：{entry["accepted"]}',
                         f'理由：{prop.get("reasoning")}',f'反馈：{after["feedback"]}',
                         f'地点：{after["location"]}；持有：{after["hands"]}；主线：{r["scores"]["quest"]}']
                if variant=='OracleGoalStack':
                    for a in r['decision']['attempts']:
                        if not a.get('executed'):exceptions.append(dict(id=ident,step=r['step'],kind='native_retry_or_reconsideration',attempt=a))
            save(REPORTS/'timelines'/f'{ident}__{variant}.md','\n\n'.join(text))
            if variant=='OracleGoalStack':
                summary=read(path.parent/'summary.json');p['variants'][variant]['status']=summary['status']
                if summary['status']=='agent_decision_exhausted':exceptions.append(dict(id=ident,kind='agent_decision_exhausted',details=read(path.parent/'decision_exhausted.json')))
                for q in qq:
                    accounting.append(dict(id=ident,step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],status=q['status'],
                        input_tokens=q.get('usage',{}).get('prompt_tokens',0),output_tokens=q.get('usage',{}).get('completion_tokens',0),cost_usd=q.get('cost_usd',0),
                        context_chars=sum(len(m['content']) for m in q['messages']),injected=q['step']==s['step']+1,
                        finish_reason=q.get('raw_response',{}).get('choices',[{}])[0].get('finish_reason')))
                    if q.get('parse_exception') or q['status']!='ok':exceptions.append(dict(id=ident,step=q['step'],kind='provider_or_json',request=q))
        pairs.append(p)
    write(RESULTS/'paired_comparison.json',pairs);gzwrite(RESULTS/'evidence_index.jsonl.gz',audit);gzwrite(RESULTS/'exceptions.jsonl.gz',exceptions)
    with (RESULTS/'request_accounting.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(accounting[0]),lineterminator='\n');w.writeheader();w.writerows(accounting)
    local=counts(pairs,'successful_original_retry');gain=loss=chgain=chloss=0
    for p in pairs:
        a=p['variants']['OriginalRecovery']['full'];b=p['variants']['OracleGoalStack']['full']
        gain+=b['main_final']>a['main_final'];loss+=b['main_final']<a['main_final']
        chgain+=b['chapter1']>a['chapter1'];chloss+=b['chapter1']<a['chapter1']
    local_net=local['OracleGoalStack_only']-local['OriginalRecovery_only']
    verdict='SUPPORT_GOAL_STACK' if gain-loss>=3 or chgain-chloss>=3 else 'PARTIAL_SUPPORT' if local_net>=3 else 'NO_SUPPORT'
    write(RESULTS/'summary.json',dict(pairs=10,independent_parent_episodes=1,local_pair_counts=local,local_net=local_net,
        main_better=gain,main_worse=loss,chapter_better=chgain,chapter_worse=chloss,pre_registered_verdict=verdict,
        variants={v:dict(actions=sum(p['variants'][v]['actions'] for p in pairs),
            recovery20=sum(p['variants'][v]['windows']['20']['successful_original_retry'] for p in pairs),
            recovery_full=sum(p['variants'][v]['full']['successful_original_retry'] for p in pairs),
            main_scores=[p['variants'][v]['full']['main_final'] for p in pairs],
            chapter1=sum(p['variants'][v]['full']['chapter1'] for p in pairs),
            rejected20=sum(p['variants'][v]['windows']['20']['rejected'] for p in pairs),
            repeated_original_rejections20=sum(len(p['variants'][v]['windows']['20']['repeated_original_rejection_steps']) for p in pairs),
            rejected_full=sum(p['variants'][v]['full']['rejected'] for p in pairs),
            wait=sum(p['variants'][v]['full']['wait'] for p in pairs),
            requests=sum(p['variants'][v]['requests'] for p in pairs),
            input_tokens=sum(p['variants'][v]['tokens_in'] for p in pairs),output_tokens=sum(p['variants'][v]['tokens_out'] for p in pairs),
            cost_usd=sum(p['variants'][v]['cost_usd'] for p in pairs)) for v in VARIANTS},
        common_peak_rate_reference_usd={v:sum(p['variants'][v]['common_peak_rate_reference_usd'] for p in pairs) for v in VARIANTS},
        analysis_model_calls=0,production_agent_changes=0,injection='first_decision_only',
        caveat='One parent, dependent checkpoints, single unpaired model sample; a one-shot partially specified hierarchy, not a persistent omniscient stack.'))
    print(json.dumps(read(RESULTS/'summary.json')),flush=True)

if __name__=='__main__':main()
