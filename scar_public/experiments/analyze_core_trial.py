"""Predeclared paired analysis; incomplete blocks are never silently dropped."""
import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path
import random
import statistics

from scar_public.provider import usage_summary

ARMS=('prompt','checked','sentry','v16')
GAMES=('remnant','mark','metropolis')


def exact_flip(differences):
    observed=abs(sum(differences))
    return sum(abs(sum(s*d for s,d in zip(signs,differences)))>=observed-1e-10
               for signs in product((-1,1),repeat=len(differences)))/(2**len(differences))


def interval(by_game):
    # Statistical resampling seed only; never enters world generation or actors.
    rng=random.Random(20261017);means=[]
    for _ in range(20000):
        sample=[rng.choice(by_game[g]) for g in GAMES for _ in by_game[g]]
        means.append(statistics.mean(sample))
    means.sort()
    return [means[int(.025*len(means))],means[int(.975*len(means))]]


def longest(actions):
    best=current=0;last=None
    for action in actions:
        current=current+1 if action==last else 1;last=action;best=max(best,current)
    return best


def summarize_arm(root):
    status=json.loads((root/'current.json').read_text())
    rows=[json.loads(p.read_text()) for p in sorted((root/'trace').glob('*.json'))]
    assert status['complete'] and len(rows)==status['steps']
    parsed=[json.loads(r['response']) for r in rows]
    packets=[r['core_packet'] for r in parsed if 'core_packet' in r]
    gates=[r['core_gate'] for r in parsed if 'core_gate' in r]
    elapsed=[r.get('core_compute_ms',0) for r in parsed if 'core_compute_ms' in r]
    actions=[r['action'] for r in rows]
    cp=root/'checkpoints'/f"{status['steps']:04d}"/'agent.json'
    memory=json.loads(cp.read_text())
    bank=memory.get('resource_evidence',{})
    return dict(steps=len(rows),quest=status['scores']['quest'],deaths=status['scores']['death'],
        passed=any(r.get('main_quest_passed') or 'completed the main quest and passed the game' in r['next_observation'] for r in rows),
        scores=status['scores'],actor_input_tokens=sum(r['input_tokens'] for r in rows),
        actor_output_tokens=sum(r['output_tokens'] for r in rows),
        inspect_actions=sum(a.startswith('inspect ') for a in actions),
        longest_action_run=longest(actions),semantic_failures=sum('Cannot ' in r['next_observation'] for r in rows),
        gate_overrides=sum(r['changed'] for r in gates),gate_reasons=dict(Counter(r['reason'] for r in gates)),
        recommendations=sum(bool(p['recommendation']) for p in packets),
        evidence_rejections=sum(bool(p['evidence_rejection']) for p in packets),
        candidate_packets=sum(bool(p['candidates']) for p in packets),
        evidence_events=dict(Counter(e['kind'] for e in bank.get('audit',[]))),
        sentry_interventions=sum(r.get('sentry_intervention',False) for r in rows),
        planning_ms_total=sum(elapsed),planning_ms_mean=statistics.mean(elapsed) if elapsed else None,
        planning_ms_max=max(elapsed) if elapsed else None,
        actor_seconds=sum(r['actor_seconds'] for r in rows)),rows,parsed


def prefix_audit(left,right,lp,rp):
    first=None;checks=0
    for a,b,x,y in zip(left,right,lp,rp):
        assert a['observation']==b['observation'] and a['before_digest']==b['before_digest'], 'Premature environment divergence'
        assert x['core_packet']==y['core_packet'], 'Unequal same-history evidence packets'
        assert x['core_gate']['proposed']==y['core_gate']['proposed'], 'Unequal same-history final LLM proposal'
        if a['action']!=b['action']:
            first=dict(step=a['step'],prompt=a['action'],checked=b['action'],
                same_packet=True,same_final_llm_proposal=True,checked_gate=y['core_gate'],
                recommendation=y['core_packet']['recommendation'])
            break
        assert a['after_digest']==b['after_digest'] and a['next_observation']==b['next_observation']
        checks+=1
    return dict(matched_prefix_transitions=checks,first_action_difference=first)


def analyze(root):
    plan=json.loads((root/'evaluation_plan.json').read_text())
    assert len(plan['jobs'])==9
    blocks=[]
    for job in plan['jobs']:
        path=root/'evaluation'/f"{job['game']}_r{job['repeat']}"
        assert (path/'result.json').exists(), f'Incomplete block: {path.name}'
        arms={};traces={};parsed={}
        for arm in ARMS: arms[arm],traces[arm],parsed[arm]=summarize_arm(path/arm)
        blocks.append(dict(game=job['game'],repeat=job['repeat'],arms=arms,
            initial=json.loads((path/'initial_receipt.json').read_text()),
            prefix_audit=prefix_audit(traces['prompt'],traces['checked'],parsed['prompt'],parsed['checked'])))
    comparisons={}
    for baseline in ('prompt','sentry','v16'):
        diffs=[b['arms']['checked']['quest']-b['arms'][baseline]['quest'] for b in blocks]
        by_game={g:[d for d,b in zip(diffs,blocks) if b['game']==g] for g in GAMES}
        comparisons[baseline]=dict(differences=diffs,mean_difference=statistics.mean(diffs),
            wins=sum(d>0 for d in diffs),ties=diffs.count(0),losses=sum(d<0 for d in diffs),
            family_means={g:statistics.mean(d) for g,d in by_game.items()},
            exact_two_sided_sign_flip_p=exact_flip(diffs),exploratory_stratified_bootstrap95=interval(by_game))
    ordered=sorted(('prompt','sentry'),key=lambda a:comparisons[a]['exact_two_sided_sign_flip_p'])
    previous=0
    for i,arm in enumerate(ordered):
        previous=max(previous,min(1,(2-i)*comparisons[arm]['exact_two_sided_sign_flip_p']))
        comparisons[arm]['holm_p']=previous
    totals={arm:dict(mean_quest=statistics.mean(b['arms'][arm]['quest'] for b in blocks),
        passed=sum(b['arms'][arm]['passed'] for b in blocks),
        deaths=sum(b['arms'][arm]['deaths'] for b in blocks),
        gate_overrides=sum(b['arms'][arm]['gate_overrides'] for b in blocks),
        actor_input_tokens=sum(b['arms'][arm]['actor_input_tokens'] for b in blocks),
        actor_output_tokens=sum(b['arms'][arm]['actor_output_tokens'] for b in blocks),
        inspect_actions=sum(b['arms'][arm]['inspect_actions'] for b in blocks),
        planning_ms_total=sum(b['arms'][arm]['planning_ms_total'] for b in blocks)) for arm in ARMS}
    stable=all(comparisons[a]['mean_difference']>0 and comparisons[a]['holm_p']<.05 and
        sum(x>0 for x in comparisons[a]['family_means'].values())>=2 and
        all(x>=0 for x in comparisons[a]['family_means'].values()) and
        not any(b['arms'][a]['passed'] and not b['arms']['checked']['passed'] for b in blocks)
        for a in ('prompt','sentry'))
    result=dict(blocks=blocks,totals=totals,comparisons=comparisons,stable_improvement_established=stable,
        evaluation_usage=usage_summary(root/'evaluation'),all_iteration_usage=usage_summary(root),
        qualification='Three familiar game families, three independent post-freeze draws each. No unseen-family or universal guarantee.')
    (root/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:result[k] for k in ('totals','comparisons','stable_improvement_established','all_iteration_usage')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    analyze(p.parse_args().root)
