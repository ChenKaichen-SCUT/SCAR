"""Offline interface checks and real-state minimal reproductions; no fixes."""
import contextlib
import io
from collections import Counter
from .common import *


def main():
    forbid_network();integrity=check_freeze()
    from agents.llm_agent_config import LLMAgentConfig
    from scar_v3.state import PublicState
    from scar_stage18_fixed.agent import Controller18Fixed
    from scar_stage16.state import PublicRuleState
    from scar_stage18 import arbitration,execution_context
    parser=LLMAgentConfig();metrics=[];request_index=[]
    for method in METHODS:
        records=rows(RESULTS/'agent_audit'/f'{method}.jsonl.gz')
        requests=rows(source(method)/'requests.jsonl.gz')
        original=rows(source(method)/'trajectory.jsonl.gz')
        contexts=[];fallbacks=[];decoding_mismatches=[];memory_lengths=[]
        for r,q,t in zip(records,requests,original):
            assert q['step']==r['step']==t['step'] and r['model_request_id']==q['request_id']
            messages='\n'.join(m['content'] for m in q['messages'])
            assert r['observation']['text'] in messages
            state=r['internal_before'];mem=state['memory']
            assert all(s in messages for s in (mem if isinstance(mem,list) else [mem]))
            memory_lengths.append(len(mem))
            with contextlib.redirect_stdout(io.StringIO()):parsed=parser.response_parser(q['raw_response']['choices'][0]['message']['content'])
            expected=r['decision']['proposed_action'] if method=='Stage18-Fixed' else r['selected_action']
            if parsed['action']!=expected:decoding_mismatches.append(r['step'])
            raw=q.get('parsed_json')
            fallback=not isinstance(raw,dict) or not all(k in raw for k in ('reasoning','action')) or not isinstance(raw.get('action'),str)
            if fallback:fallbacks.append(r['step'])
            request_index.append(dict(method=method,step=r['step'],request_id=q['request_id'],
                observation_complete=True,saved_history_included=True,parsed_action=parsed['action'],
                executed_action=r['selected_action'],fallback=fallback,status=q['status'],
                finish_reason=q['raw_response']['choices'][0]['finish_reason'],
                prompt_tokens=q['usage']['prompt_tokens'],completion_tokens=q['usage']['completion_tokens'],
                cost_usd=q['cost_usd']))
        assert not decoding_mismatches
        receipt=read(RESULTS/'agent_audit'/f'{method}.receipt.json')
        if method=='LongContextAgent':
            assert all(records[i]['internal_before']['memory']==records[i-1]['internal_after']['memory'] for i in range(1,300))
            assert all(records[i]['internal_after']['memory'].startswith(records[i]['internal_before']['memory']) for i in range(300))
        else:assert max(memory_lengths)==5
        summary=read(source(method)/'summary.json')
        metrics.append(dict(method=method,steps=300,requests=len(requests),
            observation_in_prompt_exact=300,saved_memory_in_prompt_exact=300,
            parsed_proposal_exact=300,exact_saved_final_memory=receipt['exact_saved_final_memory'],
            save_load_roundtrip_exact=receipt['save_load_roundtrip_exact'],fallback_steps=fallbacks,
            native_invalid_steps=[r['step'] for r in original if r['invalid_action']],
            output_finish_reasons=dict(Counter(q['raw_response']['choices'][0]['finish_reason'] for q in requests)),
            request_status=dict(Counter(q['status'] for q in requests)),
            input_min=min(q['usage']['prompt_tokens'] for q in requests),
            input_max=max(q['usage']['prompt_tokens'] for q in requests),
            input_first=requests[0]['usage']['prompt_tokens'],input_last=requests[-1]['usage']['prompt_tokens'],
            input_tokens=summary['input_tokens'],output_tokens=summary['output_tokens'],cost_usd=summary['cost_usd'],
            cache_hit_tokens=sum(q['usage'].get('prompt_cache_hit_tokens',0) for q in requests),
            memory_limit=5 if method!='LongContextAgent' else None,
            memory_first_size=memory_lengths[0],memory_last_size=memory_lengths[-1],
            memory_size_unit='records' if method!='LongContextAgent' else 'characters'))
    rr=rows(RESULTS/'agent_audit'/'Stage18-Fixed.jsonl.gz');reproductions=[]
    # Exercise real frozen observations/serialized states, not an invented policy.
    for n in [32,64,68,70,184,200,300]:
        r=rr[n-1];c=Controller18Fixed.from_dict(r['internal_before']['controller'])
        observed_goal=PublicState.observe(r['observation']).goal
        status=PublicRuleState(c.legacy_copy()).get_goal_status()
        assert c.target=='enter hall' and status['goal']=='hall' and not status['complete']
        assert status==r['decision']['execution_context']['goal']
        reproductions.append(dict(id='goal_contract_a'+str(n),step=n,target=c.target,
            public_goal_parser_output=observed_goal,location=c.table.state['location'],
            completion_status=status,
            observation_contains_explicit_oak_objective='remy says: Craft an oak rod.' in r['observation']['text'],
            source='scar_v3/state.py:PublicState.observe; scar_sequence/planner.py:Controller.observe; scar_stage16/state.py:PublicRuleState.get_goal_status'))
    for n in [33,35,65,67,68,69,179]:
        r=rr[n-1];d=r['decision'];c=Controller18Fixed.from_dict(d['controller_before']);a=d['stage18']
        action,reason=arbitration.choose(c,d['proposed_action'],a['bounded_candidate'],a['assessments'])
        assert action==r['selected_action'] and reason==a['reason']
        reproductions.append(dict(id='arbitration_a'+str(n),step=n,proposal=d['proposed_action'],
            candidate=a['bounded_candidate'],executed=action,reason=reason,checks=a['assessments'],
            source='scar_stage18/arbitration.py:choose',
            scope='Exact local frozen arbitration, no modified controller or new model response'))
    # Each game provides its native action space; compare methods within game.
    # Across games, retain actual prompt hashes rather than assume equality.
    prompt_checks=[]
    for game in ('mark','remnant','metropolis'):
        base_system=rows(ROOT/'results/stage22/runs'/f'{game}__LongContextAgent'/'requests.jsonl.gz')[0]['messages'][0]['content']
        for method in METHODS:
            q=rows(ROOT/'results/stage22/runs'/f'{game}__{method}'/'requests.jsonl.gz')
            passed=all(x['messages'][0]['content'].startswith(base_system+'\nPersistent public facts.') if method=='Stage18-Fixed' else x['messages'][0]['content']==base_system for x in q)
            assert passed,(game,method,'system prompt')
            prompt_checks.append(dict(game=game,method=method,requests=len(q),same_official_system_prefix=True,
                official_prefix_sha256=__import__('hashlib').sha256(base_system.encode()).hexdigest(),
                only_scar_registered_fact_append=method=='Stage18-Fixed'))
    write(RESULTS/'engineering_checks.json',dict(passed=True,methods=metrics,reproductions=reproductions,
        system_prompt_checks=prompt_checks,api_calls=0,**integrity,
        confirmed_transport_or_serialization_defect=False,permissible_patch_gate_met=False,
        patch_applied=False,patched_ab_runs=0,verdict='DESIGN_LIMIT'))
    gzwrite(RESULTS/'request_audit.jsonl.gz',request_index)
    print(json.dumps(dict(passed=True,decisions=900,reproductions=len(reproductions),new_api_calls=0)),flush=True)


if __name__=='__main__':main()
