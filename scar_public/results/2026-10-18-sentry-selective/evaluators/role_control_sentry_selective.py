"""Post-batch diagnostic; fixed policy, reversed roles for ALL16 disagreements.

The old forced repair becomes ordinary; the old ordinary candidate becomes
the repair. Its rationale replaces repair explanations, with uncertainty
explicitly left unverified. No observed future outcome enters either prompt.
This is a constructed candidate test in real states, not an on-policy result
or a pure label-only ablation (repair-card metadata necessarily differs).
"""
import concurrent.futures,copy,gzip,json
from pathlib import Path
from scar_public.sentry_selective import SelectiveRepair
from scar_public.sentry_persistent import fingerprint
from scar_public.experiments.sentry_persistent_trial import TrialProvider
from scar_public.provider import usage_summary
root=Path('/root/scar_sentry_selective_20261018');old=Path('/root/scar_sentry_persistent_20261018_v2/evaluation')
key='/root/scar_research_20261015/private/deepseek.key';read=lambda p:json.loads(p.read_text())
jobs=[]
for original in read(root/'diagnostic.json')['rows']:
    if not original['event']['comparison_calls']:continue
    game=original['game'];step=original['step']
    trace=[read(old/game/'execute/trace'/f'{n:04d}.json') for n in range(1,step+1)]
    card=copy.deepcopy(next(e['card'] for e in trace[-2]['persistent_events'] if e['type']=='persistent_card'))
    proposal=trace[-1]['response'];ordinary=trace[-1]['proposed']
    card['next']=dict(action=ordinary['action'],kind='change',changes=ordinary['reasoning'],
        preconditions='Unverified candidate; assess from the supplied public history.',
        resource_check='Unverified candidate; assess from the supplied public history.',
        expected='Outcome unknown; ordinary actor rationale: '+ordinary['reasoning'],outcomes=[])
    card['hypothesis']=ordinary['reasoning'];card['revision']='Counterfactual candidate comparison; no execution result is supplied.'
    history=[dict(cycle=-1,action='',observation=trace[0]['observation'])]
    history += [dict(cycle=t['step']-1,action=t['action'],observation=t['next_observation']) for t in trace[:-1]]
    request=next((root/'diagnostic_api'/game/str(step)).glob('*.request.json.gz'))
    packet=json.loads(json.loads(gzip.decompress(request.read_bytes()))['messages'][-1]['content'])
    jobs.append(dict(game=game,step=step,card=card,proposal=proposal,history=history,
        observation=trace[-1]['observation'],system=packet['action_schema'],audit=original.get('counterfactual')))

def evaluate(job):
    game=job['game'];step=job['step'];out=root/'role_control_api'/game/str(step)
    provider=TrialProvider(out,key,shared=root/'role_control_shared'/game);provider.arm='role_control';provider.step=step-1
    control=SelectiveRepair(provider,job['system']);control.records=job['history']
    control.pending=dict(step=step-1,observation_hash=fingerprint(job['observation']),card=job['card'])
    selected=control.choose(step-1,job['observation'],job['proposal'])
    return dict(game=game,step=step,ordinary=job['proposal'],repair=job['card']['next'],selected=selected,
        event=control.events[-1],usage=usage_summary(out),counterfactual=job['audit'])

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(evaluate,jobs))
summary=dict(cases=len(rows),replacements=sum(r['event']['changed'] for r in rows),
    corrected_prior_introduced_error=sum(r['event']['changed'] and r['counterfactual']['actual_feedback_error'] and not r['counterfactual']['proposed_feedback_error'] for r in rows),
    reversed_prior_error_removal=sum(r['event']['changed'] and r['counterfactual']['proposed_feedback_error'] and not r['counterfactual']['actual_feedback_error'] for r in rows))
(root/'role_control.json').write_text(json.dumps(dict(qualification=__doc__,summary=summary,rows=rows),ensure_ascii=False,indent=2))
print(json.dumps(summary))
