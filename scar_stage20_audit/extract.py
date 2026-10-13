"""Replay archived decisions on detached controllers, with saved replies only."""
from .common import *
deny_network()
import subprocess
from collections import Counter
from scar.io import digest
from scar_stage20.evidence import snapshot,check
from scar_stage20_audit.public import enumerate_candidates,shadow
from scar.agents.scar.repair import valid_syntax
from utils import dynamic_load_game_class


def main():
    # Protect every tracked pre-audit file, including source, raw records and reports.
    tracked=subprocess.check_output(['git','ls-tree','-r','-z','--name-only',BASE],cwd=ROOT).decode().rstrip('\0').split('\0')
    protected={name:sha(ROOT/name) for name in tracked}
    frozen=load(SOURCE/'freeze.json')
    for p,h in frozen['files'].items():assert sha(ROOT/p)==h,p
    for p,h in load(SOURCE/'artifact_manifest.json')['files'].items():assert sha(ROOT/p)==h,p
    prior=dict(base_commit=BASE,files=protected,runtime_ledger_sha256=sha(ROOT/'runtime/stage20/budget.sqlite'))
    if (RESULTS/'protected_manifest.json').exists():assert load(RESULTS/'protected_manifest.json')==prior
    else:write(RESULTS/'protected_manifest.json',prior)
    tasks=load(SOURCE/'tasks.json');states=[];stalls=[];index=[];all_decisions=0;no_plan_checks=0
    for task in tasks:
        tid=task['task_id'];rows=read_gzip(folder(tid)/'trajectory.jsonl.gz');terminal=load(folder(tid)/'terminal_decision.json')
        requests=read_gzip(folder(tid)/'requests.jsonl.gz');summary=load(folder(tid)/'summary.json')
        qs={(q['step'],q['ordinal']):q for q in requests}
        decisions=[(r['step'],r['observation'],r['decision']['decision'],r['physical_before']['state_hash'],'trajectory.jsonl.gz') for r in rows]
        if terminal['decision']['decision'].get('executed_action') is None:
            decisions.append((len(rows)+1,terminal['public_observation'],terminal['decision']['decision'],summary['final_state_hash'],'terminal_decision.json'))
        for step,obs,d,state_hash,source in decisions:
            c=controller(d['controller_before']);action=c.choose(obs)
            for ordinal,plan in enumerate(d['planning_calls'],1):
                assert not action and c.can_request(),(tid,step,ordinal)
                c.start_request();records=snapshot(c,obs)
                assert records==plan['evidence_snapshot']['records'],(tid,step,ordinal,'snapshot')
                q=qs[step,ordinal];assert q['status']=='ok' and plan['proposal']==q['parsed']
                state=c.to_dict();prediction=shadow(c,plan['proposal']);old_reason,_=check(c,plan['proposal'])
                acc=c.accept(plan['proposal'])
                assert acc==plan['acceptance'],(tid,step,ordinal,'acceptance')
                ident=f'{tid}:d{step:03d}:p{ordinal}'
                record=dict(id=ident,task_id=tid,decision_step=step,ordinal=ordinal,physical_state_hash=state_hash,
                    controller=state,observation=obs,plan=plan,request_id=q['request_id'],request_signature=q['signature'],
                    source=str((folder(tid)/source).relative_to(ROOT)),source_line=step if source.endswith('.gz') else None,
                    request_source=str((folder(tid)/'requests.jsonl.gz').relative_to(ROOT)),
                    old_evidence_reason=old_reason,shadow=prediction)
                states.append(record);index.append({k:record[k] for k in ('id','task_id','decision_step','ordinal','physical_state_hash','request_id','source','source_line','request_source')})
                action=c.choose(obs)
                if not action:action=c.choose(obs,allow_fallback=True)
            if not action and not d['planning_calls']:
                action=c.choose(obs,allow_fallback=True)
            assert action==d['executed_action'],(tid,step,action,d['executed_action'])
            all_decisions+=1;no_plan_checks+=not d['planning_calls']
        if summary['status']=='method_stalled':
            c=controller(terminal['decision']['controller']);native_agent=dynamic_load_game_class(task['game_name'],'agent','Agent')('agent_adam_davis','adam_davis')
            candidates=enumerate_candidates(c,rows)
            for candidate in candidates:
                candidate['syntax_valid']=valid_syntax(candidate['action'],native_agent.available_actions)
                candidate['eligible_public_trial']=candidate['syntax_valid'] and candidate['known_conditions_allow']
            last=load(ROOT/'runtime/stage20/runs'/f'{tid}__SCAR20/latest.json')['checkpoint']
            cp=ROOT/'runtime/stage20/runs'/f'{tid}__SCAR20'/last
            assert load(cp/'meta.json')['state_hash']==summary['final_state_hash']
            assert load(cp/'stage20.json')['controller']==terminal['decision']['controller']
            state=dict(task_id=tid,task=dict(game_name=task['game_name'],target_item=task['target_item'],initial_seed=task['initial_seed']),
                terminal_step=len(rows),physical_state_hash=summary['final_state_hash'],public_observation=terminal['public_observation'],
                controller=c.to_dict(),last_15_actions=rows[-15:],candidates=candidates,
                checkpoint=str(cp.relative_to(ROOT)),checkpoint_meta_sha256=sha(cp/'meta.json'),checkpoint_pickle_sha256=sha(cp/'physical.pkl'))
            stalls.append(state)
    assert len(states)==191 and len(stalls)==11
    rejects=[r for r in states if r['old_evidence_reason']=='evidence_unrelated_to_execution_entry'];assert len(rejects)==44
    gzip_rows(RESULTS/'planning_states.jsonl.gz',states);gzip_rows(RESULTS/'terminal_states.jsonl.gz',stalls)
    write(RESULTS/'state_index.json',index)
    write(RESULTS/'extraction_receipt.json',dict(passed=True,decisions_reconstructed=all_decisions,without_planning=no_plan_checks,
        exact_planning_snapshots_and_acceptances=len(states),stalled_checkpoints=len(stalls),evidence_rejections=len(rejects),
        old_files_protected=len(protected),new_model_calls=0,tokens=0,cost_usd=0,network_attempts=NETWORK_ATTEMPTS))
    print(json.dumps(dict(plans=len(states),stalls=len(stalls),rejections=Counter(r['shadow']['category'] for r in rejects))))


if __name__=='__main__':main()
