import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
from scar.io import atomic_json
from scar_public.provider import usage_summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--structured',type=Path,required=True);p.add_argument('--historical',type=Path,required=True)
    a=p.parse_args();main=json.loads((a.structured/'analysis.json').read_text());rows=[];counts=Counter()
    for item in main['full_games']:
        block=item['block'];row=dict(block=block,off=item['off']['scores']['quest'],
                                     advice=item['advice']['scores']['quest'],repair=item['repair']['scores']['quest'])
        if block.startswith('remnant'):
            generic=dict(scores=item['off']['scores'],changes=0,steps=300,episode_steps=300,
                         main_quest_passed=item['off']['main_quest_passed'])
        else:
            b=a.root/'branches'/block
            result=json.loads((b/'result.json').read_text());generic=result['results']['repair']
            traces=[json.loads(f.read_text()) for f in sorted((b/'repair/trace').glob('*.json'))]
            generic['episode_steps']=result['protocol']['start']+len(traces)
            generic['main_quest_passed']=any('completed the main quest and passed the game' in r['next_observation'] for r in traces)
            for r in traces:
                e=r['response']['continuation']
                counts['decisions']+=1;counts['changes']+=e['changed'];counts['repair_calls']+='proposal' in e
                counts['authority_changes']+='proposal' in e and r['action']!=e['proposal']['action']
        row['generic']=generic['scores']['quest'];row['generic_details']=generic
        for arm in ('sentry','v16'):
            data=json.loads((a.historical/'evaluation'/block/arm/'current.json').read_text())
            row[arm]=data['scores']['quest']
        rows.append(row)
    report=dict(rows=rows,counts=dict(counts),usage=usage_summary(a.root/'branches'),
                qualification='Development comparison; same trigger/query rule, endogenous total query counts differ.')
    report['aggregate']={}
    for arm in ('off','advice','repair','generic','sentry','v16'):
        delta=[r[arm]-r['off'] for r in rows]
        report['aggregate'][arm]=dict(mean_quest=statistics.mean(r[arm] for r in rows),
            sum_quest=sum(r[arm] for r in rows),deltas_vs_off=delta,
            wins=sum(v>0 for v in delta),ties=sum(v==0 for v in delta),losses=sum(v<0 for v in delta))
    report['structured_minus_generic']=[r['repair']-r['generic'] for r in rows]
    atomic_json(a.root/'analysis.json',report);print(json.dumps(report['aggregate'],indent=2))


if __name__=='__main__':main()
