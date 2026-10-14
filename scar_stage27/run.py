"""Raw proposal probes, not a modified AGC policy or a formal game run."""
import argparse
import contextlib
import copy
import gzip
import io
import json
import tempfile
from .common import *
from .fixtures import make_messages,compile_state,provenance_check
from scar_stage24.provider import SharedProvider

def execute(sample,condition):
    from scar.environment import restore,state_digest
    from scar.io import digest
    from agents.agc.state import extract
    from agents.agc.control import Control as Monitor
    from scar.agents.scar.repair import valid_syntax
    ident=sample['id'];out=RESULTS/'probes'/ident/condition
    if (out/'result.json').exists():return read(out/'result.json')
    folder=RUNTIME/'requests'/ident/condition;folder.mkdir(parents=True,exist_ok=True)
    provider=SharedProvider(folder,RUNTIME,ROOT.parent/'miyao.txt')
    if condition=='understanding':
        provider.begin_step(0);messages=make_messages(sample,condition)
        assert digest(messages)==sample['input_hashes'][condition]
        response=provider.generate(messages[-1]['content'],system_prompt=messages[0]['content'])
        try:answer=json.loads(response['response'])
        except (ValueError,TypeError):answer=None
        result=dict(id=ident,condition=condition,answer=answer,response=response['response'],status='answered' if isinstance(answer,dict) else 'invalid_json')
    else:
        cp=RESULTS/'checkpoints'/ident
        prefix=json.loads(gzip.decompress((cp/'public_prefix.json.gz').read_bytes()))
        original=copy.deepcopy(sample['original_messages']);chain=[]
        with tempfile.TemporaryDirectory(prefix='scar27-probe-') as tmp:
            env=restore(gzip.decompress((cp/'physical.pkl.gz').read_bytes()),tmp)
            assert state_digest(env)==sample['post_state_hash'] and env.obs[AGENT_ID]==sample['post_failure_observation']
            monitor=Monitor();monitor.initialize(prefix[0]['observation'])
            for p in prefix:monitor.progress(p['observation'],p['action'],p['feedback'],p['step'])
            syntax_space=env.agents[0].available_actions
            for turn in range(1,sample['recovery_horizon']+1):
                if env.steps>=300:break
                before=copy.deepcopy(env.obs[AGENT_ID]);before_hash=state_digest(env)
                state=compile_state(prefix);provenance_check(state,prefix)
                messages=make_messages(sample,condition,original=original,state=state)
                if turn==1:assert digest(messages)==sample['input_hashes'][condition]
                provider.begin_step(turn)
                response=provider.generate(messages[-1]['content'],system_prompt=messages[0]['content'])
                try:proposal=json.loads(response['response'])
                except (ValueError,TypeError):proposal=None
                action=proposal.get('action') if isinstance(proposal,dict) else None
                syntax=isinstance(action,str) and valid_syntax(action.strip(),syntax_space)
                record=dict(turn=turn,step=env.steps+1,proposal=proposal,response=response['response'],
                    observation=before,state_hash_before=before_hash,messages_hash=digest(messages),syntax_valid=syntax)
                if not syntax:
                    record.update(status='proposal_invalid',accepted=False);chain.append(record);break
                action=action.strip()
                with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:action});env.update_scores(reward)
                after=copy.deepcopy(obs[AGENT_ID]);parsed=extract(after)
                progress=monitor.progress(before,action,after,env.steps)
                accepted=not parsed['failed'] and not info.get('step_invalid_action',{}).get(AGENT_ID,False)
                record.update(action=action,feedback=after,status='executed',accepted=accepted,
                    reward=vars(reward[AGENT_ID]),scores=copy.deepcopy(env.scores[AGENT_ID]),
                    state_hash=state_digest(env),info=info,done=bool(done),public_progress=progress,
                    same_as_trigger=action==sample['candidate_action'],
                    repeats_prior_failed_action=any(p['action']==action and extract(p['feedback'])['failed'] for p in prefix))
                chain.append(record);prefix.append(dict(step=env.steps,action=action,observation=before,feedback=after))
                # Diagnostic continuation: same frozen base input, followed by
                # the actual probe transcript. No new goals or instructions.
                original[-1]['content']+='\n\nOffline replay continuation:\nPrevious model JSON: '+response['response']+'\nActual environment observation:\n'+after['text']+'\nWhat should I do next? Return only the JSON object.'
                if done:break
        result=dict(id=ident,condition=condition,status='complete',chain=chain,
            is_formal_agent_run=False,agc_arbitration_applied=False,first_input_exact_saved=condition=='A')
    qq=[json.loads(x) for x in provider.audit.read_text().splitlines()]
    gzwrite(out/'requests.jsonl.gz',qq)
    result.update(new_requests=len(qq),cost_usd=sum(q.get('cost_usd',0) for q in qq),
        input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq))
    write(out/'result.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--condition',choices=['understanding','A','B'],required=True);a=p.parse_args()
    check_freeze();sample=next(s for s in samples() if s['id']==a.id)
    print(json.dumps(execute(sample,a.condition)),flush=True)
