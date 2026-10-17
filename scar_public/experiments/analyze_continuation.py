"""All-case development analysis; includes unchanged worlds and both revisions."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics

from scar.io import atomic_json
from scar_public.provider import usage_summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--previous',type=Path,required=True);p.add_argument('--historical',type=Path,required=True)
    a=p.parse_args()
    plan=json.loads((a.root/'plan.json').read_text())
    report=dict(qualification='Post-development historical worlds; no independent or unseen-domain performance claim.',
                full_games=[],initial_branches=[],paired_checks={},mechanism={},usage={})
    totals={arm:Counter() for arm in ('off','advice','repair')}
    changed=[]
    for job in plan['jobs']:
        block=job['block'];root=a.root/'branches'/block
        result=json.loads((root/'result.json').read_text())
        report['full_games'].append(dict(block=block,**result['results']))
        series={}
        oldrows=[json.loads(f.read_text()) for f in sorted((a.historical/'evaluation'/block/'checked/trace').glob('*.json'))]
        for arm in ('off','advice','repair'):
            rows=[json.loads(f.read_text()) for f in sorted((root/arm/'trace').glob('*.json'))]
            series[arm]=rows
            rewards=[r['scores']['quest'] for r in oldrows[:job['start']]]+[r['scores']['quest'] for r in rows]
            # Main-quest completion can terminate early; pad its achieved score
            # for the fixed-budget descriptive area, not for action/cost counts.
            rewards += [rewards[-1]]*(300-len(rewards))
            report['full_games'][-1][arm]['mean_score_over_budget']=statistics.mean(rewards)
            report['full_games'][-1][arm]['episode_steps']=job['start']+len(rows)
            report['full_games'][-1][arm]['main_quest_passed']=any(
                'completed the main quest and passed the game' in r['next_observation'] for r in rows)
            for r in rows:
                e=r['response']['continuation'];c=totals[arm]
                c['suffix_decisions']+=1;c['triggers']+=bool(e['trigger']);c['repair_calls']+='proposal' in e
                c['changed']+=e['changed']
                packet=r['response']['core_packet']
                c['logical_actor_calls']+=1+bool(packet['candidates'] or packet['evidence_rejection'] or
                                                packet['observed_check']['status']=='contradicted')+('proposal' in e)
                if 'proposal' in e:
                    c['authority_changes']+=r['action']!=e['proposal']['action']
                if e['changed']:
                    c[e['trigger']['kind']]+=1
                    changed.append(dict(block=block,arm=arm,step=r['step'],original=e['original'],
                                        actor=e['proposal']['action'],executed=r['action'],reason=e['reason']))
        matched=0;first_difference=None
        for x,y in zip(series['advice'],series['repair']):
            assert x['before_digest']==y['before_digest'], (block,'before common-prefix')
            ex=x['response']['continuation'];ey=y['response']['continuation']
            assert x['response']['core_packet']==y['response']['core_packet']
            assert x['response']['core_initial_proposal']==y['response']['core_initial_proposal']
            assert ex.get('packet')==ey.get('packet') and ex.get('proposal')==ey.get('proposal')
            matched+=1
            if x['action']!=y['action']:
                first_difference=x['step'];break
            assert x['after_digest']==y['after_digest']
            assert x['response'].get('frame')==y['response'].get('frame')
        report['paired_checks'][block]=dict(matched_decisions=matched,first_authority_difference=first_difference)
    for i in range(3):
        block=f'remnant_r{i}'
        control=json.loads((a.root/'controls'/f'{block}.json').read_text())
        assert control['decisions']==300 and control['new_api_calls']==0
        old=json.loads((a.historical/'evaluation'/block/'checked/current.json').read_text())
        rows=[json.loads(f.read_text()) for f in sorted((a.historical/'evaluation'/block/'checked/trace').glob('*.json'))]
        common=dict(scores=old['scores'],changes=0,triggers=0,done=old['done'],steps=300,
                    episode_steps=300,main_quest_passed=old['main_quest_passed'],
                    mean_score_over_budget=statistics.mean(r['scores']['quest'] for r in rows))
        report['full_games'].append(dict(block=block,**{arm:common for arm in ('off','advice','repair')},control=control))
    for block in sorted((a.previous/'branches').iterdir()):
        report['initial_branches'].append(dict(block=block.name,results=json.loads((block/'result.json').read_text())['results']))
    report['mechanism']={arm:dict(counts) for arm,counts in totals.items()}
    report['changed_actions']=changed
    report['usage']={name:usage_summary(root/'branches') for name,root in [('revision1',a.previous),('revision2',a.root)]}
    report['aggregate']={}
    for arm in ('off','advice','repair'):
        rows=report['full_games'];deltas=[r[arm]['scores']['quest']-r['off']['scores']['quest'] for r in rows]
        report['aggregate'][arm]=dict(mean_quest=statistics.mean(r[arm]['scores']['quest'] for r in rows),
            quest_sum=sum(r[arm]['scores']['quest'] for r in rows),deltas_vs_off=deltas,
            wins=sum(v>0 for v in deltas),ties=sum(v==0 for v in deltas),losses=sum(v<0 for v in deltas),
            deaths=sum(r[arm]['scores']['death'] for r in rows),
            completions=sum(r[arm]['main_quest_passed'] for r in rows),
            mean_score_over_budget=statistics.mean(r[arm]['mean_score_over_budget'] for r in rows))
    atomic_json(a.root/'analysis.json',report)
    print(json.dumps({k:report[k] for k in ('aggregate','mechanism','usage')},indent=2))


if __name__=='__main__':main()
