"""All eligible prior decisions, fixed proposals, no future outcomes in prompts."""
import concurrent.futures,copy,json
from pathlib import Path
from scar_public.sentry_selective import SelectiveRepair,replacement_allowed
from scar_public.sentry_persistent import fingerprint
from scar_public.experiments.sentry_persistent_trial import TrialProvider
from scar_public.provider import usage_summary
root=Path('/root/scar_sentry_selective_20261018_v2');old=Path('/root/scar_sentry_persistent_20261018_v2')
key='/root/scar_research_20261015/private/deepseek.key'
read=lambda p:json.loads(p.read_text())
jobs=[]
for game in ('remnant','mark','metropolis'):
    traces=[read(p) for p in sorted((old/'evaluation'/game/'execute/trace').glob('*.json'))]
    # Saved actor request carries exactly the publicly supplied action schema.
    import gzip
    system=None
    for path in sorted((old/'evaluation'/game/'execute/api').glob('*.request.json.gz')):
        data=json.loads(gzip.decompress(path.read_bytes()))
        messages=data.get('messages',data.get('payload',{}).get('messages',[]))
        if messages and 'Action space' in messages[0].get('content',''):
            system=messages[0]['content'];break
    if system is None:
        # The common schema can also be read from a saved repair request.
        for path in sorted((old/'evaluation'/game/'execute/api').glob('*.request.json.gz')):
            data=json.loads(gzip.decompress(path.read_bytes()));messages=data.get('messages',data.get('payload',{}).get('messages',[]))
            try:packet=json.loads(messages[-1]['content'])
            except (ValueError,IndexError):continue
            if 'action_schema' in packet:system=packet['action_schema'];break
    assert system is not None,game
    history=[dict(cycle=-1,action='',observation=traces[0]['observation'])];card=None
    audits={r['step']:r for r in read(old/(game+'_action_audit.json'))['records']}
    for row in traces:
        choice=next(e for e in row['persistent_events'] if e['type']=='persistent_choice')
        if choice['eligible']:
            assert card and card['status']=='act'
            jobs.append(dict(game=game,row=row,card=copy.deepcopy(card),history=copy.deepcopy(history),system=system,audit=audits.get(row['step'])))
        history.append(dict(cycle=row['step']-1,action=row['action'],observation=row['next_observation']))
        cards=[e['card'] for e in row['persistent_events'] if e['type']=='persistent_card']
        card=cards[-1] if cards else None

def evaluate(job):
    game=job['game'];row=job['row'];step=row['step']-1;out=root/'diagnostic_api'/game/str(row['step'])
    provider=TrialProvider(out,key,shared=root/'diagnostic_shared'/game);provider.arm='diagnostic';provider.step=step
    control=SelectiveRepair(provider,job['system']);control.records=job['history']
    control.pending=dict(step=step,observation_hash=fingerprint(row['observation']),card=job['card'])
    proposed=row['proposed'];selected=control.choose(step,row['observation'],proposed)
    if selected['action']==proposed['action']:assert selected is proposed
    result=dict(game=game,step=row['step'],ordinary=proposed,repair=job['card']['next']['action'],
        selected=selected,event=control.events[-1],usage=usage_summary(out))
    event=control.events[-1]
    if event['comparison']:
        reverse_id='B' if event['ordinary_id']=='A' else 'A'
        try:allowed,reason=replacement_allowed(event['comparison'],job['history'],reverse_id)
        except (ValueError,KeyError,TypeError) as exc:allowed=False;reason=str(exc)
        result['reverse']=dict(changed=allowed,reason=reason,additional_model_calls=0)
    # Attach evaluator-only outcomes AFTER inference is complete.
    if job['audit']:result['counterfactual']=job['audit']
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(evaluate,jobs))
summary=dict(eligible=len(rows),disagreements=sum(r['ordinary']['action']!=r['repair'] for r in rows),
    replacements=sum(r['event']['changed'] for r in rows),comparison_calls=sum(r['event']['comparison_calls'] for r in rows),
    introduced_errors_before=0,introduced_errors_after=0,removed_errors_before=0,removed_errors_after=0)
summary['reverse_replacements']=sum(r.get('reverse',{}).get('changed',False) for r in rows)
summary['reverse_corrected_prior_introduced_error']=0
summary['reverse_undid_prior_error_removal']=0
for r in rows:
    a=r.get('counterfactual')
    if not a:continue
    introduced=a['actual_feedback_error'] and not a['proposed_feedback_error']
    removed=a['proposed_feedback_error'] and not a['actual_feedback_error']
    summary['introduced_errors_before']+=introduced;summary['introduced_errors_after']+=introduced and r['event']['changed']
    summary['removed_errors_before']+=removed;summary['removed_errors_after']+=removed and r['event']['changed']
    summary['reverse_corrected_prior_introduced_error']+=introduced and r.get('reverse',{}).get('changed',False)
    summary['reverse_undid_prior_error_removal']+=removed and r.get('reverse',{}).get('changed',False)
(root/'diagnostic.json').write_text(json.dumps(dict(summary=summary,rows=rows),ensure_ascii=False,indent=2))
print(json.dumps(summary),flush=True)
