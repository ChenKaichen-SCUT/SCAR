"""Exhaustive saved-action, controller and model-context audit; zero inference calls."""
import re
import csv
import json
from collections import Counter
from agents.agc.state import extract
from scar_stage27.fixtures import failure_type
from .common import *

def norm(s):return ' '.join(str(s or '').lower().split())
def contains(haystack,needle):return bool(needle and norm(needle) in norm(haystack))
def accepted(r):return not extract(r['feedback'])['failed'] and not re.search(r'^Failed to\b',extract(r['feedback'])['feedback'],re.I) and not r['info'].get('step_invalid_action',{}).get(AGENT_ID,False)

def main():
    offline();records=[];segments=[];summaries=[];index=[]
    for ident in CASES:
        for variant in ['Original','OracleRecovery']:
            s,rr,qq,path,lines=data(ident,variant);first_goal=rr[0]['control_after']['goal']['goal_description'];seen_failures={};seq=[]
            requests={}
            for q in qq:requests.setdefault(q['step'],[]).append(q)
            for r in rr:
                step=r['step'];proposal=r['decision']['attempts'][-1]['proposal'];control=r['control_after'];before=r['decision']['control_before']
                state=extract(r['feedback']);g=control['goal'];archive=control['archive'];previous_goal=(before.get('goal') or {}).get('goal_description')
                assert r['action']==r['decision']['executed_action'] and not r['decision']['controller_generated_action']
                assert len(archive)<=8 and len(r['memory_before'])<=5
                qstep=requests[step];messages='\n'.join(m['content'] for q in qstep for m in q['messages']);last=qstep[-1]
                assert proposal==r['decision']['attempts'][-1]['proposal']
                rejected=not accepted(r);failure=state['feedback'] if rejected else None
                prior=seen_failures.get(r['action'],[])[:]
                if rejected:seen_failures.setdefault(r['action'],[]).append(step)
                archive_text='\n'.join(x['goal_description'] for x in archive)
                rec=dict(id=ident,variant=variant,step=step,continuation_step=step-s['step'],source_trajectory=path,source_line=lines[step],
                    original_goal=s['current_goal'],injected_recovery_objective=CASES[ident],first_recovery_goal=first_goal,
                    action=r['action'],reasoning=proposal.get('reasoning',''),goal_description=g['goal_description'],previous_goal=previous_goal,
                    goal_changed=g['goal_description']!=previous_goal,goal_status=g['status'],goal_confidence=g['confidence'],goal_events=control['events'],
                    accepted=not rejected,public_feedback=state['feedback'],failure_type=failure_type(failure) if failure else None,
                    prior_same_action_rejection_steps=prior,original_action_retry=r['action']==s['candidate_action'],
                    original_action_success=r['action']==s['candidate_action'] and not rejected,main_delta=r['reward']['quest'],death_delta=r['reward']['death'],
                    scores=r['scores'],main_quest_progress=r['main_quest_progress'],transition=r['transition'],
                    original_exact_in_archive=contains(archive_text,s['current_goal']),original_exact_in_current_goal=norm(g['goal_description'])==norm(s['current_goal']),
                    original_exact_in_model_context=contains(messages,s['current_goal']),original_exact_in_accepted_request=contains('\n'.join(m['content'] for m in last['messages']),s['current_goal']),
                    recovery_exact_in_archive=contains(archive_text,first_goal),recovery_exact_in_model_context=contains(messages,first_goal),
                    archive_goals=[x['goal_description'] for x in archive],memory_entries=len(r['memory_before']),
                    native_requests=len(qstep),model_request_ids=[q['request_id'] for q in qstep],
                    current_public_state={k:state[k] for k in ['location','hands','equipment','ground','observed_container_contents','npcs']},
                    state_hash=r['state_hash'],state_hash_before=r['state_hash_before'])
                records.append(rec);seq.append(rec)
                if not segments or segments[-1]['id']!=ident or segments[-1]['variant']!=variant or segments[-1]['goal']!=g['goal_description']:
                    segments.append(dict(id=ident,variant=variant,start=step,end=step,goal=g['goal_description'],actions=1,rejections=int(rejected),deaths=r['reward']['death'],main_gain=r['reward']['quest']))
                else:
                    z=segments[-1];z['end']=step;z['actions']+=1;z['rejections']+=int(rejected);z['deaths']+=r['reward']['death'];z['main_gain']+=r['reward']['quest']
            seg=[x for x in segments if x['id']==ident and x['variant']==variant]
            summaries.append(dict(id=ident,variant=variant,actions=len(seq),goal_segments=len(seg),rejections=sum(not x['accepted'] for x in seq),
                repeated_rejections=sum(not x['accepted'] and bool(x['prior_same_action_rejection_steps']) for x in seq),
                original_action_success_steps=[x['step'] for x in seq if x['original_action_success']],
                current_goal_original_exact_steps=[x['step'] for x in seq if x['original_exact_in_current_goal']],
                original_archived_context_absent_steps=[x['step'] for x in seq if x['original_exact_in_archive'] and not x['original_exact_in_model_context']],
                original_context_present_steps=[x['step'] for x in seq if x['original_exact_in_model_context']],
                original_archive_present_steps=[x['step'] for x in seq if x['original_exact_in_archive']],
                first_model_context_original_absent=next((x['step'] for x in seq if not x['original_exact_in_model_context']),None),
                first_goal_exact_segment_end=seg[0]['end'],main_final=rr[-1]['scores']['quest'],chapter=rr[-1]['main_quest_progress']['chapter'],
                failure_counts=dict(Counter(x['failure_type'] for x in seq if not x['accepted'])),native_model_requests=sum(x['native_requests'] for x in seq)))
            # Compact full suffix, not a sampled set of supportive actions.
            dest=REPORTS/'timelines'/f'{ident}__{variant}.md';dest.parent.mkdir(parents=True,exist_ok=True)
            def cell(x):return str(x).replace('|','/').replace('\n',' / ')
            content=f'# {ident} / {variant}\n\n原目标：{s["current_goal"]}\n\n恢复条件：{CASES[ident]}\n\n原失败动作：`{s["candidate_action"]}`。以下为全部 {len(seq)} 个动作；完整理由/状态/请求见逐动作数据库及原轨迹。\n\n'
            content+='|动作号|动作|公开结果|当前目标|状态|主线增量|原目标在归档/上下文（字面）|\n|---|---|---|---|---|---|---|\n'
            content+='\n'.join('|'+ '|'.join(cell(t) for t in [x['step'],x['action'],x['public_feedback'][:230],x['goal_description'],x['goal_status'],x['main_delta'],str(x['original_exact_in_archive'])+'/'+str(x['original_exact_in_model_context'])])+'|' for x in seq)+'\n'
            dest.write_text(content)
            index.append(dict(id=ident,variant=variant,source_trajectory=path,source_failure_step=s['step'],timeline=str(dest.relative_to(ROOT)),
                actions=[dict(step=x['step'],source_line=x['source_line'],request_ids=x['model_request_ids'],state_hash=x['state_hash']) for x in seq]))
    assert len(records)==3116
    gzwrite(RESULTS/'action_audit.jsonl.gz',records);write(RESULTS/'goal_segments.json',segments);write(RESULTS/'trajectory_statistics.json',summaries)
    gzwrite(RESULTS/'evidence_index.jsonl.gz',index)
    write(RESULTS/'extraction_summary.json',dict(total_actions=len(records),paired_checkpoints=10,independent_parent_episodes=1,
        unique_source_actions=len({(r['source_trajectory'],r['step']) for r in records}),
        saved_request_occurrences=sum(r['native_requests'] for r in records),unique_saved_request_ids=len({q for r in records for q in r['model_request_ids']}),
        original_goal_archive_but_not_context_actions=sum(r['original_exact_in_archive'] and not r['original_exact_in_model_context'] for r in records),
        controller_generated_actions=0,new_model_calls=0))
    print(json.dumps(read(RESULTS/'extraction_summary.json')),flush=True)

if __name__=='__main__':main()
