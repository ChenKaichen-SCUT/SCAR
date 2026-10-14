"""Offline evidence indexes, goal segments and supplemental cycle audit.

No diagnostics from this module are available to the experimental policy.
"""
from collections import Counter
from .common import *
from .analyze import final_folder
from agents.agc.state import extract


def main():
    offline();check_freeze();evidence=[];diagnostics=[]
    for game in GAMES:
        for method in ['Stage18-Fixed','AGC']:
            folder=final_folder(game) if method=='AGC' else source(game)
            rr=rows(folder/'trajectory.jsonl.gz');segments=[];events=[];no_reward=0;max_no_reward=0
            for i,r in enumerate(rr):
                d=r['decision'];public=extract(r['feedback']);n=r['step']
                goal=d['attempts'][-1]['proposal']['goal_description'].strip() if method=='AGC' else d['controller_before']['target']
                if not segments or segments[-1]['goal']!=goal:
                    segments.append(dict(start=n,end=n,goal=goal,actions=Counter(),quest_gain=0,informative_steps=0))
                seg=segments[-1];seg['end']=n;seg['actions'][r['action']]+=1;seg['quest_gain']+=r['reward']['quest']
                if method=='AGC':seg['informative_steps']+=r['transition']['informative']
                no_reward=0 if r['reward']['quest'] else no_reward+1;max_no_reward=max(max_no_reward,no_reward)
                item=dict(game=game,method=method,step=n,action=r['action'],goal=goal,feedback=public['feedback'],
                    public_failed=public['failed'],quest_increment=r['reward']['quest'],quest_total=r['scores']['quest'],
                    official_invalid=r['invalid_action'],location=public['location'],hands=public['hands'],
                    reference=str(folder.relative_to(ROOT)/'trajectory.jsonl.gz')+f':{i+1}')
                if method=='AGC':
                    item.update(goal_status=r['control_after']['goal']['status'],last_progress_step=r['control_after']['goal']['last_progress_step'],
                        goal_creation_step=r['control_after']['goal']['creation_step'],progress=r['transition'],
                        proposal=d['attempts'][0]['proposal'],attempts=d['attempts'],events=r['control_after']['events'])
                else:item.update(controller_generated_action=d['intercepted'],proposed_action=d['proposed_action'],
                    executed_action=d['executed_action'],controller_details_reference=item['reference']+'#decision')
                evidence.append(item)
                if r['reward']['quest'] or r['reward'].get('death') or r['invalid_action'] or public['failed']:
                    events.append({k:item[k] for k in ('step','action','feedback','quest_increment','quest_total','reference')})
            for s in segments:
                s['length']=s['end']-s['start']+1;s['action_counts']=s.pop('actions').most_common()
            # Post-hoc supplemental metric: 20 actions with <=5 unique actions,
            # <=1 new observed state and no quest reward. Not a policy trigger.
            sm=rows(RESULTS/'step_metrics'/f'{game}__{method}__final.jsonl.gz')
            cycling=[]
            for i in range(19,len(rr)):
                window=rr[i-19:i+1];pro=sm[i-19:i+1]
                if len(set(r['action'] for r in window))<=5 and sum(r['progress']['observation_new'] for r in pro)<=1 and not sum(r['reward']['quest'] for r in window):
                    cycling.append(i+1)
            diagnostics.append(dict(game=game,method=method,goal_segments=segments,events=events,
                longest_no_quest_reward_run=max_no_reward,posthoc_cycle_window_end_steps=cycling,
                cycle_metric_scope='Supplemental descriptive metric defined after reading metropolis; no tuning or policy changes; not independent evidence of causal failure.'))
    gzwrite(RESULTS/'evidence.jsonl.gz',evidence);write(RESULTS/'trajectory_diagnostics.json',diagnostics)
    print(json.dumps(dict(evidence_rows=len(evidence),new_model_calls=0)))

if __name__=='__main__':main()
