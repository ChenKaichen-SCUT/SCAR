"""Real-engine matched frozen-proposal experiment; never mutates game state.

Only the evaluator sees checkpoint objects. Policy code sees public text and
previously declared hypotheses. Shadow veto checks do not update the policy.
"""
import argparse
import contextlib
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

from scar.environment import AGENT_ID, restore, isolated_copy
from scar_public.obligations import ExecutionModel
from scar_public.resource_competition import ResourceGap
from scar_public.resource_evidence import EvidenceBank
from scar_public.resource_trial import from_public, make_trial, public_outcome, fresh


def execute(env,action):
    with contextlib.redirect_stdout(sys.stderr):
        obs,reward,done,info=env.step({AGENT_ID:action})
        env.update_scores(reward)
    return obs[AGENT_ID]['text'],bool(done)


def endpoint(env,text):
    # Scores are updated in place by the engine; freeze the measurement now.
    return dict(public=fresh(text),scores=json.loads(json.dumps(env.scores)),observation=text)


def run(rows,checkpoint,out,enabled,first=184,last=250):
    out.mkdir(parents=True,exist_ok=False);env=restore(checkpoint,out)
    model=ExecutionModel();previous=None
    for row in rows[:first-1]:
        model.observe(row['observation'],previous);previous=row['action']
    text=env.obs[AGENT_ID]['text']
    assert text==rows[first-1]['observation']
    model.observe(text,previous)
    bank=EvidenceBank();trace=[];vetoes=[];cost=0;first_session=None;done=False
    original_start=endpoint(env,text)
    for original in rows[first-1:last]:
        action=original['action'];review=None;p=None
        if action.startswith('craft '):
            try:
                p=from_public(model,text,action.split()[-1])
                if enabled:review=bank.review_action(p,action)
            except ResourceGap: pass
        if original['step']==first:
            assert p is not None
            report,first_session=make_trial(model,text,p.target)
            assert first_session and first_session.action()==action
            _,acquisition_meta=bank.query(p)
        if review:
            # A separate evaluator tests the veto in an isolated actual engine.
            # It contributes to validation cost, not to the agent's trajectory.
            with isolated_copy(env) as shadow:
                shadow_scores=json.loads(json.dumps(shadow.scores))
                check,check_done=execute(shadow,action)
                same_scores=shadow_scores==shadow.scores
            actual=public_outcome(check,action)
            veto=dict(proposal_step=original['step'],action=action,review=review,
                before=text,shadow_observation=check,shadow_status=actual,
                shadow_same_public_physical_state=fresh(text)==fresh(check),shadow_same_scores=same_scores)
            vetoes.append(veto)
            if actual!='failure' or fresh(text)!=fresh(check) or not same_scores:
                raise AssertionError('False veto in actual engine; do not count as a saving')
            continue
        before=text
        text,done=execute(env,action);cost+=1
        model.observe(text,action)
        row=dict(proposal_step=original['step'],environment_action=cost,action=action,
                 observation=before,next_observation=text,environment_done=done)
        if original['step']==first:
            event=first_session.observe(text)
            row['acquisition_feedback']=event
            if enabled:bank.observe(first_session.compiled,event,acquisition_meta['epoch'])
            row['acquisition_certificate']=report
            assert first_session.action() is None, 'acquisition suffix not executed by this protocol'
        trace.append(row)
        if done: break
    result=dict(arm='reuse' if enabled else 'control',proposal_first=first,proposal_last=last,
        api_calls=0,environment_actions=cost,acquisition_actions=1,
        validation_actions=len(vetoes),vetoes=vetoes,trace=trace,
        start=original_start,endpoint=endpoint(env,text),environment_done=done,ledger=bank.state,
        limitation='Frozen future proposal stream, not a free-running LLM or a new full game')
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('arm','environment_actions','acquisition_actions','validation_actions','environment_done')}),flush=True)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();rows=json.loads(a.public.read_text(encoding='utf-8'))
    a.output.mkdir(parents=True,exist_ok=False)
    start=perf_counter();control=run(rows,a.checkpoint,a.output/'control',False)
    reuse=run(rows,a.checkpoint,a.output/'reuse',True)
    summary=dict(checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
        public_input_sha256=hashlib.sha256(a.public.read_bytes()).hexdigest(),
        seconds=perf_counter()-start,control_actions=control['environment_actions'],
        reuse_actions=reuse['environment_actions'],acquisition_actions=1,
        saved_actions=control['environment_actions']-reuse['environment_actions'],
        savings_minus_entire_acquisition_charge=control['environment_actions']-reuse['environment_actions']-1,
        veto_steps=[r['proposal_step'] for r in reuse['vetoes']],
        all_vetoes_really_failed=all(r['shadow_status']=='failure' for r in reuse['vetoes']),
        same_final_visible_state=control['endpoint']['public']==reuse['endpoint']['public'],
        same_scores=control['endpoint']['scores']==reuse['endpoint']['scores'],
        control_done=control['environment_done'],reuse_done=reuse['environment_done'],
        evaluator_validation_actions=reuse['validation_actions'],api_calls=0,
        warnings=['Acquisition occurs in both arms; subtracting it again is a conservative separate accounting.',
                  'Equal final observed state does not establish hidden-state equality.',
                  'A shorter unsuccessful trajectory is not successful game completion.'])
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
