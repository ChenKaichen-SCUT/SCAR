"""Independent zero-network policy/accounting verification after native replay."""
from .common import *
deny_network()
import argparse
import copy
import gzip
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from scar.io import digest
from scar.providers.deepseek import estimate_cost,ModelResponseError
from scar_stage14.knowledge import Knowledge
from .agent import make_method,decision_state
from .planning import parse_response,validate
from .run_errors import MethodStalled
from .controller import Controller21
from .recovery import Recovery,blocker_id
from scar_v3.state import parse_action


def close(a,b):assert math.isclose(a,b,abs_tol=1e-10,rel_tol=1e-9),(a,b)


def ledger_rows(path):
    with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
        return db.execute('SELECT id,reserved,charged,status FROM requests ORDER BY id').fetchall()


class SavedResponses:
    """Exactly the archived model samples; no socket, provider or paid retry."""
    def __init__(self,requests):
        self.groups=defaultdict(list);self.used=[];self.step=0;self.ordinal=0
        for q in requests:self.groups[q['logical_id']].append(q)
    def begin_step(self,step):self.step=step;self.ordinal=0
    def generate(self,user_prompt,system_prompt=None,required=(),phase='action',max_tokens=None,validator=None):
        self.ordinal+=1;ident=f'{self.step:03d}:{self.ordinal:03d}'
        messages=([dict(role='system',content=system_prompt)] if system_prompt else [])+[dict(role='user',content=user_prompt)]
        signature=digest(dict(messages=messages,phase=phase,max_tokens=max_tokens,required=required))
        group=self.groups[ident];assert group and ident not in self.used
        assert all(q['messages']==messages and q['signature']==signature for q in group),(ident,'prompt signature differs')
        self.used.append(ident)
        good=[q for q in group if q['status']=='ok']
        if not good:raise ModelResponseError('Three audited API/parse attempts failed')
        q=good[-1];parsed,events=parse_response(q['raw_response']['choices'][0]['message']['content'])
        assert parsed==q['parsed'] and events==q['normalization_events']
        if validator:validator(parsed)
        u=q['usage']
        return dict(parsed=parsed,response=q['raw_response']['choices'][0]['message']['content'],num_input_tokens=u['prompt_tokens'],num_output_tokens=u['completion_tokens'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=ROOT/'runtime/stage21');args=parser.parse_args()
    freeze=load(RESULTS/'freeze.json');prior=load(RESULTS/'prior_manifest.json')['files']
    for p,h in freeze['files'].items():assert sha(ROOT/p)==h,p
    for p,h in prior.items():assert sha(ROOT/p)==h,p
    engine=Path(os.environ['AGENTODYSSEY_ROOT'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=engine,text=True).strip()==freeze['engine_commit']
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=engine,text=True).strip()
    tasks=load(RESULTS/'tasks.json');assert tasks==load(ROOT/'results/stage17/tasks.json') and len(tasks)==24
    replay=load(RESULTS/'replay_local.json');assert replay['passed'] and replay['trajectory_count']==24
    replays={r['task_id']:r for r in replay['runs']}
    histories={h['task_id']:h for h in read_gzip(RESULTS/'initial_public_histories.jsonl.gz')}
    ledger_before=ledger_rows(args.runtime/'budget.sqlite');ledger={r[0]:r for r in ledger_before}
    all_requests={};checks=[];grant_checks=[];prompt_checks=0;state_checks=0;totals=Counter()
    chains={(g['task_id'],g['id']):g for g in load(RESULTS/'etbr_chains.json')}
    for task in tasks:
        tid=task['task_id'];folder=RESULTS/'runs'/f'{tid}__SCAR21'
        summary=load(folder/'summary.json');rows=read_gzip(folder/'trajectory.jsonl.gz');requests=read_gzip(folder/'requests.jsonl.gz')
        terminal=load(folder/'terminal_decision.json');history=histories[tid]['history']
        assert digest(history)==task['initial_public_history_hash'] and summary['initial_state_hash']==task['initial_state_hash']
        assert len(rows)==summary['steps']<=100
        for q in requests:
            assert q['request_id'] not in all_requests;all_requests[q['request_id']]=q
            assert q['model']=='deepseek-flash' and q['temperature']==.7 and q['thinking']=='disabled'
            assert q['max_tokens']==512 and len(q['messages'][-1]['content'])<=8000
            assert 0<=q['attempt']<3 and q['ordinal']==1
            assert 1<=q['step']<=len(rows)+1
            close(q['cost_usd'],estimate_cost(q['usage'],freeze['model_config']['pricing_usd_per_million']))
            close(q['charged_or_reserved_usd'],q['cost_usd'])
            if q['status']=='ok':validate(q['parsed'])
            totals['requests']+=1;totals['cost_usd']+=q['charged_or_reserved_usd']
            totals['input_tokens']+=q['usage']['prompt_tokens'];totals['output_tokens']+=q['usage']['completion_tokens']
        provider=SavedResponses(requests);public=Knowledge()
        for h in history:public.observe(h['after'],h['action'],cutoff=h['after']['step'])
        with tempfile.TemporaryDirectory(prefix='scar21-independent-') as temp:
            agent=make_method('SCAR21',task['game_name'],provider,task['objective_text'],task['target_item'],history,Path(temp))
            first_obs=rows[0]['observation'] if rows else terminal['public_observation']
            public.observe(first_obs,None,cutoff=first_obs['step'])
            for row in rows:
                provider.begin_step(row['step'])
                assert public.view()==row['public_knowledge_before']
                action,*_=agent.act(row['observation'])
                assert action==row['action'],(tid,row['step'],action,row['action'])
                actual=decision_state(agent,'SCAR21')
                assert actual==row['decision'],(tid,row['step'],'saved decision mismatch')
                agent.observe_transition(row['observation'],action,row['feedback'])
                assert agent.controller.outcome20==row['mechanism_outcome'],(tid,row['step'],'outcome mismatch')
                delta=public.observe(row['feedback'],action,cutoff=row['feedback']['step'],source={'evaluation_step':row['step']})
                assert delta==row['knowledge_delta'] and public.view()==row['public_knowledge_after']
                assert agent.controller.step16==row['step'] and agent.controller.exploration_spent<=18
                totals['actions']+=1;state_checks+=1
            if summary['status']=='method_stalled':
                provider.begin_step(len(rows)+1)
                try:agent.act(terminal['public_observation'])
                except MethodStalled:pass
                else:raise AssertionError('Recorded terminal stall was not reproduced')
            else:assert summary['status']=='success',summary
            assert decision_state(agent,'SCAR21')==terminal['decision'],(tid,'terminal decision differs')
            assert set(provider.used)==set(provider.groups)
            prompt_checks+=len(provider.used)
            c=agent.controller
            assert c.observation_count20==len(history)+len(rows)
            assert c.plan_calls20<=24 and len(c.etbr21.grants)<=6
            assert len(c.etbr21.consumed)==len(set(c.etbr21.consumed))==len(c.etbr21.grants)
            counts=Counter(g['blocker_id'] for g in c.etbr21.grants);assert all(n<=2 for n in counts.values())
            for g in c.etbr21.grants:
                assert g['blocker_id']==blocker_id(g['blocker']) and g['evidence']['freshness']=='NEW'
                assert g['evidence']['observed_step']<=g['start_step']
                assert Recovery.relation(g['evidence'],g['blocker'])!='UNKNOWN'
                assert g['transit_used']<=3 and g['probe_used']<=1 and len(g['actions'])<=4
                for a in g['actions']:
                    r=rows[a['step']-1];selection=r['decision']['decision']['stage20']['stage21']['selection']
                    assert r['action']==a['action'] and selection['grant_id']==g['id']
                    assert not r['decision']['decision']['planning_calls']
                for e in g['stage_events']:
                    assert 1<=e['step']<=len(rows)
                    if e['stage']=='TASK_PROGRESS':assert rows[e['step']-1]['metrics']['actual_production']
                post=chains[tid,g['id']]
                prior_c=Controller21.from_dict(rows[g['start_step']]['decision']['decision']['controller_before'])
                strict=prior_c._all_needed(g['blocker']['subject'])
                for place,data in prior_c.table.places.items():
                    if set(data['objects']) & strict:strict.add(place)
                assert sorted(strict)==post['strict_blocker_entities']
                specific=g['evidence']['subject'] in strict or g['evidence']['object'] in strict
                assert specific==post['trigger_has_specific_blocker_support']
                for e in post['actual_material_gain_events']:
                    r=rows[e['step']-1];p=parse_action(r['action'])
                    assert p.verb in ('pick up','store','take out','buy') and p.target!=task['target_item']
                    public_c=Controller21.from_dict(r['decision']['decision']['controller_before'])
                    assert p.target in public_c._all_needed(g['blocker']['subject'])
                    gained={n:v-r['physical_before']['possessed'].get(n,0) for n,v in r['physical_after']['possessed'].items() if v>r['physical_before']['possessed'].get(n,0)}
                    assert e['physical_possession_gain']==gained and gained
                for step in post['reconstructed_production_steps']:assert rows[step-1]['metrics']['actual_production']
                for step in post['precondition_actual_steps']:
                    raw_after=rows[step]['decision']['decision']['controller_before'] if step<len(rows) else terminal['decision']['controller']
                    after_c=Controller21.from_dict(raw_after)
                    if g['blocker']['requires_ground']:assert (after_c.table.state.get('ground') or {}).get(g['blocker']['subject'],0)>0
                    else:assert after_c.ownership(g['blocker']['subject'])['lower_bound']>=g['blocker'].get('required_amount',1)
                grant_checks.append(dict(task_id=tid,id=g['id'],evidence_id=g['evidence_id'],actions=len(g['actions']),
                    implemented_broad_relation_verified=True,specific_current_blocker_support=specific,
                    posthoc_material_events=len(post['actual_material_gain_events']),posthoc_actual_precondition_steps=post['precondition_actual_steps'],
                    posthoc_production_steps=post['reconstructed_production_steps']))
        assert summary['success']==(rows[-1]['success'] if rows else False)
        assert replays[tid]['steps']==len(rows) and replays[tid]['requests']==len(requests)
        assert replays[tid]['true_success']==summary['success'] and replays[tid]['final_hash']==summary['final_state_hash']
        episode={r[0]:r for r in ledger_rows(args.runtime/'runs'/f'{tid}__SCAR21'/'budget.sqlite')}
        assert set(episode)=={q['request_id'] for q in requests}
        cost=sum(q['charged_or_reserved_usd'] for q in requests);assert cost<=.25
        for q in requests:
            r=episode[q['request_id']];close(r[1],q['reserved_usd']);close(r[2],q['charged_or_reserved_usd']);assert r[3]==q['status']
        totals['success']+=summary['success']
        checks.append(dict(task_id=tid,passed=True,actions=len(rows),requests=len(requests),status=summary['status'],cost_usd=cost))
    assert set(all_requests)==set(ledger)
    saved_ledger=load(RESULTS/'cost_ledger.json')
    assert {r['request_id'] for r in saved_ledger['requests']}==set(ledger)
    for qid,q in all_requests.items():
        r=ledger[qid];close(r[1],q['reserved_usd']);close(r[2],q['charged_or_reserved_usd']);assert r[3]==q['status']
    close(saved_ledger['committed_usd'],totals['cost_usd']);assert totals['cost_usd']<=3
    analysis=load(RESULTS/'analysis.json');s=analysis['methods']['SCAR21']
    for a,b in (('actions','steps'),('requests','api_calls'),('success','success'),('cost_usd','cost_usd'),('input_tokens','input_tokens'),('output_tokens','output_tokens')):close(totals[a],s[b])
    assert len(grant_checks)==analysis['etbr']['triggers']
    assert sum(g['specific_current_blocker_support'] for g in grant_checks)==analysis['etbr']['triggers_with_specific_blocker_evidence']
    assert sum(g['posthoc_material_events'] for g in grant_checks)==analysis['etbr']['unique_material_action_events']
    assert len(read_gzip(RESULTS/'evidence_index.jsonl.gz'))==totals['actions']==replay['real_replay_actions']
    assert ledger_before==ledger_rows(args.runtime/'budget.sqlite')
    assert not NETWORK_ATTEMPTS
    assert len(list(REPORTS.glob('*.md')))>=7
    files=[p for root in (ROOT/'scar_stage21',RESULTS,REPORTS) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    for p in files:
        data=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
        assert not re.search(rb'\bsk-[A-Za-z0-9_-]{24,}\b',data),str(p)
        assert p.stat().st_size<100*1024*1024,str(p)
    receipt=dict(passed=True,at_utc=datetime.now(timezone.utc).isoformat(),independent_process=True,network_disabled=True,
        new_model_calls=0,new_embedding_calls=0,network_attempts=0,formal_requests=totals['requests'],formal_cost_usd=totals['cost_usd'],
        all_24_initial_states_and_native_actions_verified=True,native_replay_actions=totals['actions'],
        deterministic_policy_decisions_reconstructed=state_checks+sum(r['status']=='method_stalled' for r in checks),
        logical_prompts_exact=prompt_checks,controller_states_and_outcomes_exact=True,public_knowledge_reconstructed=True,
        original_files_unchanged=len(prior),frozen_files_verified=len(freeze['files']),etbr_grants=grant_checks,
        sqlite_and_exported_ledger_match=True,old_baselines_rerun=0,completed_failures_rerun=0,secrets_scan_passed=True,runs=checks)
    write(RESULTS/'verification.json',receipt)
    write(RESULTS/'research_state.json',dict(phase='complete_local_verified',formal_started=True,total_runs=24,archived_runs=24,
        successes=totals['success'],requests=totals['requests'],cost_usd=totals['cost_usd'],research_decision=analysis['research_decision'],
        native_replay_passed=True,independent_verification_passed=True,policy_unchanged_after_freeze=True,no_further_experiments=True))
    files += [RESULTS/'verification.json',RESULTS/'research_state.json']
    write(RESULTS/'artifact_manifest.json',dict(files={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files)) if p.name!='artifact_manifest.json'},
        excludes=['self-referential manifest','downloaded dependencies','private runtime/checkpoints','credentials']))
    print(json.dumps(dict(passed=True,**totals,etbr_grants=len(grant_checks),historical_files_unchanged=len(prior))))


if __name__=='__main__':main()
