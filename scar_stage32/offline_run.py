"""Two new calls per historical candidate; no candidate resampling or rollout."""
import argparse,contextlib,copy,io,time,traceback
from scar_stage24.provider import SharedProvider
from agents.saer.reflection import calibrate
from agents.saer.state import rejected
from scar.agents.scar.repair import valid_syntax
from scar.io import digest
from .common import *
from .integration import make_agent

def execute(ident):
    from scar.environment import restore,state_digest,isolated_copy
    check_freeze(light=True);s=next(s for s in read(RESULTS/'samples.json') if s['id']==ident)
    folder=RUNTIME/'offline'/ident;out=RESULTS/'offline'/ident
    if (out/'result.json').exists():return read(out/'result.json')
    folder.mkdir(parents=True,exist_ok=True);provider=SharedProvider(folder,RUNTIME,ROOT.parent/'miyao.txt');provider.begin_step(s['step'])
    with contextlib.redirect_stdout(io.StringIO()):agent=make_agent(s['seed'],provider,folder/'memory')
    env=restore(gzip.decompress((RESULTS/'checkpoints'/s['checkpoint']/'physical.pkl.gz').read_bytes()),folder,agent)
    assert state_digest(env)==s['state_hash'];calls=[];started=time.time();result=dict(id=ident,seed=s['seed'],step=s['step'],kind=s['kind'],status='infrastructure_error')
    def call(phase,user,system):
        r=provider.generate(user_prompt=user,system_prompt=system)
        calls.append(dict(phase=phase,prompt_hash=digest(user),system_hash=digest(system),response=r['response'],input_tokens=r['num_input_tokens'],output_tokens=r['num_output_tokens']))
        return r
    def probe(action):
        before=state_digest(env)
        with isolated_copy(env) as clone:
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=clone.step({AGENT_ID:action});clone.update_scores(reward)
            p=dict(action=action,feedback=obs[AGENT_ID],reward=vars(reward[AGENT_ID]),done=bool(done),info=info,state_hash=state_digest(clone),
                accepted=not rejected(obs[AGENT_ID]) and not info.get('step_invalid_action',{}).get(AGENT_ID,False))
            if s.get('followup_action'):
                with contextlib.redirect_stdout(io.StringIO()):obs2,reward2,done2,info2=clone.step({AGENT_ID:s['followup_action']});clone.update_scores(reward2)
                p['followup']=dict(action=s['followup_action'],feedback=obs2[AGENT_ID],reward=vars(reward2[AGENT_ID]),info=info2,
                    accepted=not rejected(obs2[AGENT_ID]) and not info2.get('step_invalid_action',{}).get(AGENT_ID,False),state_hash=state_digest(clone))
        assert state_digest(env)==before;return p
    try:
        final,record=calibrate(s['candidate'],s['base_prompt'],s['system_prompt'],s['summary'],call)
        proposal=agent.cfg.json_parser(final['response']);action=proposal.get('action','') if isinstance(proposal,dict) else ''
        syntax=isinstance(action,str) and valid_syntax(action.strip(),agent.available_actions)
        candidate=probe(s['candidate']['action'].strip());actual=probe(action.strip()) if syntax and action.strip()!=s['candidate']['action'].strip() else copy.deepcopy(candidate) if syntax else None
        result.update(status='complete',record=record,calls=calls,final_proposal=proposal,final_syntax_valid=syntax,candidate_native=candidate,final_native=actual,
            changed=bool(syntax and action.strip()!=s['candidate']['action'].strip()),source_state_hash=s['state_hash'],risk_veto=False)
    except Exception as exc:result.update(error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()),calls=calls)
    qq=[json.loads(x) for x in provider.audit.read_text().splitlines()] if provider.audit.exists() else []
    gzwrite(out/'requests.jsonl.gz',qq);result.update(requests=len(qq),cost_usd=sum(q.get('cost_usd',0) for q in qq),elapsed_seconds=time.time()-started)
    write(out/'result.json',result);print(json.dumps(dict(id=ident,status=result['status'],requests=len(qq))),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);execute(p.parse_args().id)
