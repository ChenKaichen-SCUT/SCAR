"""Independent offline archive audit. No policy decisions or model requests."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from .common import ROOT, RESULTS, REPORTS, ENGINE_COMMIT, load, write, read_gzip, sha, deny_network
from .planning import FIELDS, SYSTEM, COMPLETION, parse_response, InterfaceError
from scar.io import digest
from scar_stage14.knowledge import Knowledge
from scar_v3.state import PublicState, parse_action
from scar_stage16.knowledge import PublicTable


def close(a,b):
    assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10),(a,b)


def semantic(facts):
    return {k:{f:v.get(f) for f in ('ingredients','quantities','stations','certainty')} for k,v in facts.items()}


def ledger_snapshot(path):
    with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
        return db.execute('SELECT id,reserved,charged,status FROM requests ORDER BY id').fetchall()


def completion_evidence(intent,table):
    """Check the declared completion against saved PUBLIC state, not policy choose."""
    item=intent['target'];kind=intent['type']
    if kind=='INSPECT_OBJECT':return dict(valid=item in table.inspected,basis='public inspection registered')
    if kind=='EXPLORE_FRONTIER':return dict(valid=item==table.state['location'],basis='public current location')
    if kind=='LOCATE_PRECONDITION':
        def path(name,ancestors=()):
            if name in ancestors or len(ancestors)>=8:return False
            if (table.count(name) or 0)>0 or (table.state.get('ground') or {}).get(name,0):return True
            if any(p['objects'].get(name,0)>0 and table.path(loc) for loc,p in table.places.items()):return True
            rule=table.recipes.get(name,{})
            return bool(rule.get('ingredients') and all(path(n,ancestors+(name,)) for n in rule['ingredients']+rule.get('stations',[])))
        return dict(valid=path(item),basis='bounded public reachable supply or disclosed recipe path; unknown station/quantity not proved')
    return dict(valid=(table.count(item) or 0)>=intent.get('amount',1) or kind=='CRAFT_PRECONDITION' and intent.get('crafted',False),basis='public possession or separately checked actual crafting')


def audit_plan(plan,group,obs,knowledge,registry):
    assert group and 1<=plan['context_attempt']<=2
    fs=plan['evidence_snapshot'];assert fs['snapshot_step']==obs['step']
    prompt=group[0]['messages'][-1]['content']
    assert fs['prompt_characters']==len(prompt) and obs['text'] in prompt
    text=prompt.split('PUBLIC EVIDENCE (cite IDs):\n',1)[1]
    records=[json.loads(line) for line in text.splitlines()]
    assert records==fs['records'] and len(records)<=64 and len(text)+1<=14000
    for r in records:
        assert r['id']=='E'+digest([r['kind'],r['key'],r['value']])[:12]
        assert r['first_seen_step']<=r['snapshot_step']==obs['step']
        assert r['observed_step']<=obs['step']
        if r['kind']=='recipe':
            actual=knowledge.facts[r['key']];v=r['value']
            assert set(actual.get('ingredients') or [])==set(v.get('ingredients') or [])
            assert actual.get('quantities')==v.get('quantities')
            assert set(actual.get('stations') or [])==set(v.get('stations') or [])
        assert r['id'] in registry
    if plan['status']=='ok':
        assert group[-1]['status']=='ok' and group[-1]['parsed']==plan['proposal']
        a=plan['acceptance'];assert a['proposal']==plan['proposal']
        if a['accepted']:
            refs=a['evidence_refs']
            assert [r['id'] for r in refs]==plan['proposal']['evidence_ids']
            assert all(r['first_seen_step']<=obs['step'] and r['observed_step']<=obs['step'] for r in refs)
            assert all(r['id'] in registry for r in refs)
            assert any(r['kind'] not in ('goal','blocker') and plan['proposal']['entry'] in r['names'] for r in refs)
    else:
        assert plan['status']=='interface_unavailable' and len(group)==3
        assert all(q['status']=='invalid_response' for q in group)
        assert plan['proposal'] is None and plan['acceptance'] is None


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=ROOT/'runtime/stage20')
    parser.add_argument('--key-path',type=Path,default=ROOT.parent/'miyao.txt');args=parser.parse_args()
    deny_network();ledger_before=ledger_snapshot(args.runtime/'budget.sqlite')
    freeze=load(RESULTS/'freeze.json');prior=load(RESULTS/'prior_manifest.json')['files']
    for paths in (freeze['files'],prior):
        for name,value in paths.items():assert sha(ROOT/name)==value,name
    original=load(RESULTS/'freeze_startup.json');auth=freeze['continuation_authorization']
    assert sha(RESULTS/'freeze_startup.json')==auth['original_freeze_sha256']
    assert [k for k,v in original['files'].items() if freeze['files'][k]!=v]==['scar_stage20/run.py']
    assert (RESULTS/'startup_failure/run.py.frozen').read_text().replace('agent.controller.outcome19','agent.controller.outcome20')==(ROOT/'scar_stage20/run.py').read_text()
    assert auth['user_reply']=='修复日志并续跑原24局（推荐）' and auth['new_model_requests_before_recovery']==0
    assert freeze['methods']==['SCAR20'] and freeze['site']=='local' and freeze['worker_processes']==12
    assert freeze['max_steps']==freeze['internal_P3_horizon']==100
    frozen_at=datetime.fromisoformat(freeze['created_utc']).timestamp()
    continued_at=datetime.fromisoformat(auth['utc']).timestamp()
    engine=Path(os.environ['AGENTODYSSEY_ROOT'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=engine,text=True).strip()==ENGINE_COMMIT
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=engine,text=True).strip()
    tasks=load(RESULTS/'tasks.json');assert tasks==load(ROOT/'results/stage17/tasks.json') and len(tasks)==24
    assert sha(RESULTS/'initial_public_histories.jsonl.gz')==sha(ROOT/'results/stage17/initial_public_histories.jsonl.gz')
    histories={r['task_id']:r for r in read_gzip(RESULTS/'initial_public_histories.jsonl.gz')}
    assert {p.name for p in (RESULTS/'runs').iterdir() if p.is_dir()}=={t['task_id']+'__SCAR20' for t in tasks}
    replay=load(RESULTS/'replay_local.json');assert replay['passed'] and replay['new_api_calls']==0 and replay['trajectory_count']==24
    replay_by={r['task_id']:r for r in replay['runs']}
    stats={(r['task_id'],r['method']):r for r in load(RESULTS/'per_task.json')};assert len(stats)==192
    for old in load(ROOT/'results/stage19/per_task.json'):
        assert all(stats[old['task_id'],old['method']][k]==v for k,v in old.items())
    intents={(r['task_id'],r['id']):r for r in load(RESULTS/'subgoal_outcomes.json')}
    totals=Counter();checks=[];all_requests={};all_intents=set();finishes=Counter();plan_count=0;completed_checks=[]
    for task in tasks:
        tid=task['task_id'];folder=RESULTS/'runs'/f'{tid}__SCAR20'
        summary=load(folder/'summary.json');rows=read_gzip(folder/'trajectory.jsonl.gz');requests=read_gzip(folder/'requests.jsonl.gz')
        terminal=load(folder/'terminal_decision.json');tc=terminal['decision']['controller'];td=terminal['decision']['decision']
        initial_failure=RESULTS/'startup_failure/runs'/folder.name
        startup=load(initial_failure/'summary.json');startup_terminal=load(initial_failure/'terminal_decision.json')
        assert startup['status']=='method_exception' and startup['steps']==0
        assert not read_gzip(initial_failure/'requests.jsonl.gz') and not read_gzip(initial_failure/'trajectory.jsonl.gz')
        assert rows[0]==read_gzip(RESULTS/'startup_recovery'/f'{tid}.jsonl.gz')[0]
        assert rows[0]['state_hash']==startup['final_state_hash'] and rows[0]['feedback']==startup_terminal['public_observation']
        assert 1<=len(rows)==summary['steps']<=100
        assert summary['initial_state_hash']==task['initial_state_hash'] and summary['started']>=continued_at>=frozen_at
        assert digest(histories[tid]['history'])==task['initial_public_history_hash']
        knowledge=Knowledge()
        for h in histories[tid]['history']:knowledge.observe(h['after'],h['action'],cutoff=h['after']['step'])
        knowledge.observe(rows[0]['observation'],None,cutoff=rows[0]['observation']['step'])
        groups=defaultdict(list);count=Counter()
        for q in requests:
            assert q['request_id'] not in all_requests;all_requests[q['request_id']]=q;groups[q['logical_id']].append(q)
            assert q['start']>=continued_at and q['end']>=q['start']
            assert q['phase']=='subgoal' and q['ordinal'] in (1,2) and q['attempt'] in (0,1,2)
            assert q['logical_id']==f"{q['step']:03d}:{q['ordinal']:03d}" and 2<=q['step']<=len(rows)+1
            assert q['model']=='deepseek-flash' and q['temperature']==.7 and q['thinking']=='disabled' and q['max_tokens']==768
            assert q['messages'][0]==dict(role='system',content=SYSTEM)
            assert q['signature']==digest(dict(messages=q['messages'],phase='subgoal',max_tokens=768,required=FIELDS))
            u=q['usage'];assert u==q['raw_response']['usage'] and u['total_tokens']==u['prompt_tokens']+u['completion_tokens']
            prices=freeze['model_config']['pricing_usd_per_million']
            cost=(u['prompt_cache_hit_tokens']*prices['cache_hit']+(u['prompt_tokens']-u['prompt_cache_hit_tokens'])*prices['cache_miss']+u['completion_tokens']*prices['output'])/1e6
            close(cost,q['cost_usd']);close(cost,q['charged_or_reserved_usd']);count['cost_usd']+=cost
            count['input_tokens']+=u['prompt_tokens'];count['output_tokens']+=u['completion_tokens']
            finishes[q['raw_response']['choices'][0]['finish_reason']]+=1
            raw=q['raw_response']['choices'][0]['message']['content']
            try:parsed,events=parse_response(raw)
            except InterfaceError as exc:
                assert q['status']=='invalid_response' and q['interface_error_category']==exc.category
                count['api_failed_requests']+=1
            else:
                assert q['status']=='ok' and parsed==q['parsed'] and events==q.get('normalization_events',[])
        for group in groups.values():
            assert [q['attempt'] for q in group]==list(range(len(group))) and len(group)<=3
            assert len({q['signature'] for q in group})==1 and not any(q['status']=='ok' for q in group[:-1])
        assert len(groups)==tc['plan_calls20']<=24 and max(tc['context_counts20'].values(),default=0)<=2
        assert sum(tc['context_counts20'].values())==len(groups)
        assert count['cost_usd']<=freeze['model_config']['episode_budget_usd']
        count['api_calls']=len(requests);count['logical_subgoal_requests']=len(groups)
        previous=None;last_hash=task['initial_state_hash'];inspected=Counter();execution=defaultdict(list);seen_groups=set()
        for step,row in enumerate(rows,1):
            assert row['step']==step and row['method']=='SCAR20' and row['task_id']==tid
            assert row['goal']==task['objective_text'] and row['seed']==task['initial_seed']
            assert row['physical_before']['state_hash']==last_hash
            if previous is not None:assert row['observation']==previous
            previous=row['feedback'];last_hash=row['state_hash'];assert row['physical_after']['state_hash']==last_hash
            assert row['success']==(row['physical_after']['target_owned']>=task['target_amount'] and row['target_produced_during_task']>=task['target_amount'])
            if step<len(rows):assert not row['success'] and not row['done'] and not row['death']
            assert knowledge.view()==row['public_knowledge_before']
            d=row['decision']['decision'];c=row['decision']['controller'];outcome=row['mechanism_outcome']
            assert semantic(c['table']['knowledge']['facts'])==semantic(knowledge.view())
            assert c['target']==d['controller_before']['target']==d['stage20']['original_task']=='craft 1 '+task['target_item']
            assert c['step16']==step-1 and c['observation_count20']==len(histories[tid]['history'])+step-1
            assert d['executed_action']==row['action']==outcome['action'] and d['no_action_proposal_interface']
            assert not any('consequence' in k.lower() for k in c) and d['stage20']['internal_horizon']==100
            tx=d['stage20']['transaction'];assert tx['failures_unchanged'] and tx['attempts_unchanged']
            assert tx['exploration_after']-tx['exploration_before']==bool(tx['executed_probe'])
            assert c['exploration_spent']==tx['exploration_after']
            assert d['llm_called']==bool(d['planning_calls']) and len(d['planning_calls'])<=2
            for ordinal,plan in enumerate(d['planning_calls'],1):
                lid=f'{step:03d}:{ordinal:03d}';audit_plan(plan,groups[lid],row['observation'],knowledge,tc['evidence20']);seen_groups.add(lid);plan_count+=1
            if d['active_subgoal']:
                assert d['stage20']['source']=='persistent_subgoal'
                execution[d['active_subgoal']['id']].append(dict(step=step,action=row['action']))
            delta=knowledge.observe(row['feedback'],row['action'],cutoff=row['feedback']['step'],source={'evaluation_step':step})
            assert delta==row['knowledge_delta'] and knowledge.view()==row['public_knowledge_after']
            for key,pre in outcome['preconditions'].items():
                raw=rows[pre['first_step']-1]['mechanism_outcome']['feedback']
                assert pre['raw_feedback']==raw and pre['source']=='native_missing_necessary_feedback' and pre['object_type']=='UNKNOWN'
                match=re.search(r'Cannot craft '+re.escape(pre['product'])+r'\. Missing necessary (.+?) in the current area\.',raw)
                assert match and pre['required_object'] in match[1].split(', ') and key==pre['product']+':'+pre['required_object']
                if pre['first_satisfied_step'] is not None:
                    ground=PublicState.observe(rows[pre['first_satisfied_step']-1]['feedback']).ground
                    assert ground.get(pre['required_object'],0)>0
            p=parse_action(row['action']);m=row['metrics'];count['steps']+=1
            count['controller_only_actions']+=not d['llm_called'];count['controller_only_nonwait_actions']+=not d['llm_called'] and p.verb!='wait'
            count['wait_actions']+=p.verb=='wait';count['craft_attempts']+=p.verb=='craft';count['productive_crafts']+=bool(m['actual_production'])
            for k in ('craft_failed','material_rejection','station_rejection','invalid'):count[k]+=bool(m[k])
            if p.verb=='inspect':count['repeated_inspections']+=inspected[p.target]>0;inspected[p.target]+=1
        if td.get('executed_action') is None:
            for ordinal,plan in enumerate(td.get('planning_calls',[]),1):
                lid=f'{len(rows)+1:03d}:{ordinal:03d}';audit_plan(plan,groups[lid],terminal['public_observation'],knowledge,tc['evidence20']);seen_groups.add(lid);plan_count+=1
        assert seen_groups==set(groups)
        assert tc['observation_count20']==len(histories[tid]['history'])+len(rows) and tc['step16']==len(rows)
        accepted={a['intent_id']:a for a in tc['acceptance20'] if a['accepted']}
        ends={i['id']:i for i in tc['intent_log20']}
        for active in (tc['intent20'],tc['suspended20']):
            if active and active['id'] not in ends:ends[active['id']]=dict(active,status='censored_at_episode_end',termination_reason=summary['status'])
        assert set(ends)==set(accepted)
        for ident,end in ends.items():
            saved=intents[tid,ident];all_intents.add((tid,ident))
            assert all(saved[k]==v for k,v in end.items())
            assert end['actions']==execution[ident] and end['steps']==len(execution[ident])
            assert end['completion']==COMPLETION[end['type']] and end['final_goal']==tc['target']
            if 'final_goal_unchanged' in end:assert end['final_goal_unchanged']
            assert any(e['id']==ident and e['event']=='accepted' for e in tc['lifecycle20'])
            if end['status']=='completed':
                assert end['termination_reason'] in ('real_public_completion','real_public_feedback_satisfies_condition')
                assert any(e['id']==ident and e['event']=='completed' for e in tc['lifecycle20'])
                state=rows[end['end_step']]['decision']['decision']['controller_before'] if end['end_step']<len(rows) else tc
                proof=completion_evidence(end,PublicTable(**state['table']))
                assert proof['valid'],(tid,ident,proof)
                completed_checks.append(dict(task_id=tid,intent_id=ident,type=end['type'],target=end['target'],end_step=end['end_step'],**proof))
                if end['type']=='CRAFT_PRECONDITION' and end.get('crafted'):
                    assert any(parse_action(rows[x['step']-1]['action']).target==end['target'] and rows[x['step']-1]['metrics']['actual_production'] for x in execution[ident])
        assert summary['final_state_hash']==last_hash and summary['success']==rows[-1]['success']
        if summary['status']=='method_stalled':assert tc['recovery20']['state']=='STALLED' and td['executed_action'] is None
        elif summary['status']=='success':assert summary['success']
        elif summary['status']=='step_limit':assert len(rows)==100 and not summary['success']
        elif summary['status']=='game_failure':assert rows[-1]['done'] or rows[-1]['death'] or rows[-1]['physical_after']['health']<=0
        else:raise AssertionError(('Unhandled final status; audit explicitly',tid,summary['status']))
        native=replay_by[tid]
        assert native['passed'] and native['steps']==len(rows) and native['requests']==len(requests)
        assert native['final_hash']==last_hash and native['true_success']==summary['success']
        for k,v in count.items():close(v,stats[tid,'SCAR20'].get(k,0))
        count['success']=summary['success']
        for b in (60,80,100):count['R'+str(b)]=summary['success'] and len(rows)<=b
        totals.update(count);checks.append(dict(task_id=tid,passed=True,actions=len(rows),requests=len(requests),status=summary['status'],true_success=summary['success'],final_hash=last_hash))
    assert set(intents)==all_intents and replay['real_replay_actions']==totals['steps']
    assert plan_count==totals['logical_subgoal_requests']
    ledger=load(RESULTS/'cost_ledger.json');db={r[0]:r for r in ledger_before}
    assert {r['request_id'] for r in ledger['requests']}==set(db)==set(all_requests)
    for row in ledger['requests']:
        q=all_requests[row['request_id']];s=db[row['request_id']]
        assert row['status']==q['status']==s[3]
        close(row['charged_usd'],q['charged_or_reserved_usd']);close(s[2],row['charged_usd'])
        close(row['reserved_usd'],q['reserved_usd']);close(s[1],row['reserved_usd'])
    close(ledger['committed_usd'],totals['cost_usd']);assert totals['cost_usd']<=freeze['model_config']['total_budget_usd']
    analysis=load(RESULTS/'analysis.json')['methods']['SCAR20']
    for k,v in totals.items():close(v,analysis.get(k,0))
    assert len(read_gzip(RESULTS/'evidence_index.jsonl.gz'))==totals['steps']
    assert len(read_gzip(RESULTS/'planning_outcomes.jsonl.gz'))==plan_count
    assert len(load(RESULTS/'response_errors.json'))==totals['api_failed_requests']
    preflight=load(RESULTS/'preflight_local.json');assert preflight['passed'] and preflight['api_calls']==0
    assert len(list(REPORTS.glob('*.md')))>=9
    secrets=[]
    if args.key_path.exists():
        raw=args.key_path.read_bytes().strip();secrets=re.findall(rb'sk-[A-Za-z0-9_-]{16,}',raw)
        if raw:secrets.append(raw)
    published=[p for d in (ROOT/'scar_stage20',RESULTS,REPORTS) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']+[ROOT/'scripts/run_stage20.sh']
    for p in published:
        raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
        assert not any(s in raw for s in secrets),'Secret in '+str(p.relative_to(ROOT))
        assert not re.search(rb'(?i)Bearer\s+sk-[A-Za-z0-9_-]{16,}',raw),str(p)
        assert p.stat().st_size<100*1024*1024,str(p)
    assert ledger_snapshot(args.runtime/'budget.sqlite')==ledger_before
    receipt=dict(passed=True,verified_utc=datetime.now(timezone.utc).isoformat(),site='local',independent_process=True,
        network_disabled=True,new_api_calls=0,policy_decisions_reexecuted=0,native_replay_actions=totals['steps'],
        frozen_files_verified=len(freeze['files']),historical_files_unchanged=len(prior),source_engine_commit=ENGINE_COMMIT,
        public_knowledge_reconstructed_actions=totals['steps'],request_schema_and_usage_verified=len(all_requests),
        prompt_snapshots_exact=True,request_finish_reasons=dict(finishes),cost_usd=totals['cost_usd'],
        accepted_intent_lifecycles_verified=len(intents),matched_shared_sqlite_ledger=True,secrets_scan_passed=True,
        failed_episodes_resampled=0,historical_baseline_runs_added=0,approved_runner_logging_exception=True,
        startup_failures_retained=24,exact_recovered_first_actions_in_full_native_replay=24,runs=checks,totals=dict(totals))
    receipt['public_completion_conditions_verified']=len(completed_checks)
    write(RESULTS/'completed_intent_public_checks.json',completed_checks)
    write(RESULTS/'verification.json',receipt)
    write(RESULTS/'research_state.json',dict(phase='complete_local_verified',formal_started=True,total_runs=24,archived_runs=24,
        success=totals['success'],new_api_requests=totals['api_calls'],cost_usd=totals['cost_usd'],native_replay_passed=True,
        independent_verification_passed=True,no_further_experiments=True,policy_unchanged_after_freeze=True,
        approved_runner_logging_fix=True,startup_failures_preserved=24))
    published += [RESULTS/'verification.json',RESULTS/'research_state.json',RESULTS/'completed_intent_public_checks.json']
    manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(published)) if p.name!='artifact_manifest.json'}
    write(RESULTS/'artifact_manifest.json',dict(files=manifest,includes_analysis_and_reports=True,
        excludes=['this self-referential manifest','downloaded dependencies','private runtime/checkpoints','credentials']))
    print(json.dumps(dict(passed=True,runs=24,actions=totals['steps'],requests=totals['api_calls'],cost_usd=totals['cost_usd'],artifacts=len(manifest))))


if __name__=='__main__':main()
