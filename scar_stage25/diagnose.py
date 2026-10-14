"""Evidence indices and confidence plots from saved observations only."""
from collections import Counter
from agents.agc.state import extract
from .common import *


def main():
    offline();check_freeze();metrics=read(RESULTS/'metrics.json');evidence=[];diagnostics=[]
    for game in GAMES:
        ident=case_id(game,42);folder=RESULTS/'runs'/ident
        rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz')
        index={(q['step'],q['ordinal']):(i+1,q) for i,q in enumerate(qq)}
        m=next(r for r in metrics if r['game']==game and r['method']=='AGC-v2')
        retries=[];unverified=[];confidence_reasons=Counter();failures=Counter();failed_steps=[]
        for r in rr:
            n=r['step'];d=r['decision'];parsed=extract(r['feedback'])
            requests=[]
            for a in d['attempts']:
                line,q=index[n,a['ordinal']]
                requests.append(dict(ordinal=a['ordinal'],request_line=line,request_id=q['request_id'],
                    proposed_action=(a['proposal'] or {}).get('action'),hard=a['hard'],reasons=a['reasons'],
                    executed=a['executed'],evidence_verified=a['evidence_verified'],
                    finish_reason=q['raw_response']['choices'][0]['finish_reason'],parse_exception=q.get('parse_exception')))
            evidence.append(dict(case=ident,step=n,trajectory_line=n,trajectory=str((folder/'trajectory.jsonl.gz').relative_to(ROOT)),
                requests_file=str((folder/'requests.jsonl.gz').relative_to(ROOT)),requests=requests,
                executed_action=r['action'],public_failed=parsed['failed'],main_delta=r['reward']['quest'],main_total=r['scores']['quest'],
                confidence_after=r['control_after']['goal']['confidence'],goal_after=r['control_after']['goal']['goal_description']))
            if d['action_retry_calls']:
                retries.append(dict(step=n,requests=requests,executed=r['action'],feedback=parsed['feedback'],main_delta=r['reward']['quest']))
            if any(not a['evidence_verified'] for a in d['attempts']):
                unverified.append(dict(step=n,quotes=[(a['proposal'] or {}).get('goal_evidence') for a in d['attempts'] if not a['evidence_verified']],
                    executed=r['action'],hard_reasons=[a['reasons'] for a in d['attempts'] if a['hard']]))
            for e in r['control_after']['events']:
                if e['kind']=='confidence_update':confidence_reasons.update(e['reasons'])
            if parsed['failed']:
                # Verbatim public feedback, no hidden rule-based grouping.
                failures[parsed['feedback'].split('\n')[0]]+=1
                failed_steps.append(dict(step=n,action=r['action'],feedback=parsed['feedback']))
        segments=sorted(m['goal_segments'],key=lambda s:s['length'],reverse=True)[:5]
        main_last=m['quest_milestones'][-1]['step'] if m['quest_milestones'] else 0
        tail=[r for r in rr if r['step']>main_last]
        low=[x for x in m['reset_windows'] if x['low_confidence']]
        diag=dict(game=game,action_retry_decisions=retries,unverified_evidence_decisions=unverified,
            confidence_update_reasons=dict(confidence_reasons),public_failure_messages=failures.most_common(),public_failed_steps=failed_steps,
            longest_goals=segments,last_main_progress_step=main_last,tail_without_main_progress=len(tail),
            tail_action_counts=Counter(r['action'] for r in tail).most_common(),
            low_confidence_resets=len(low),low_confidence_resets_with_main_gain=sum(x['main_success'] for x in low),
            all_resets_with_main_gain=sum(x['main_success'] for x in m['reset_windows']),
            right_censored_reset_windows=sum(x['right_censored'] for x in m['reset_windows']),
            zero_action_reset_windows=sum(x['actual_actions']==0 for x in m['reset_windows']))
        diagnostics.append(diag)
        # Small case excerpts selected by transparent rules plus explicit report references.
        selected={1,len(rr),main_last,main_last+1}
        selected.update(r['step'] for r in retries)
        selected.update(r['step'] for r in m['quest_milestones'])
        selected.update({'remnant':[42,50,175,177,216,245,246,247,248,249,250],
                         'mark':[77,81,82,83,162,163,165,166,167,170,171,173,176,187,200,275],
                         'metropolis':[24,34,50,60,80,100,150,200,240]}[game])
        excerpts=[]
        for n in sorted(selected):
            if not 1<=n<=len(rr):continue
            r=rr[n-1]
            excerpts.append(dict(step=n,action=r['action'],before=r['observation']['text'],after=r['feedback']['text'],
                main_reward=r['reward']['quest'],main_total=r['scores']['quest'],goal=r['control_after']['goal'],
                events=r['control_after']['events'],attempts=[dict(proposal=a['proposal'],reasons=a['reasons'],executed=a['executed']) for a in r['decision']['attempts']]))
        write(RESULTS/'case_evidence'/f'{game}.json',excerpts)
    gzwrite(RESULTS/'evidence_index.jsonl.gz',evidence);write(RESULTS/'diagnostics.json',diagnostics)
    fairness=[]
    for game in GAMES:
        mm=[r for r in metrics if r['game']==game]
        assert len({r['initial_state_hash'] for r in mm})==1
        configs={r['method']:read(ROOT/r['source_folder']/'config.json') for r in mm}
        initial=[read(ROOT/r['source_folder']/'initial_public.json') for r in mm]
        assert all(p['observation']==initial[0]['observation'] and p['previous_history']==initial[0]['previous_history'] for p in initial)
        assert all(c['max_steps']==300 for c in configs.values())
        params={}
        for field in ['model','temperature','top_p','presence_penalty','max_tokens','thinking']:
            values={json.dumps(q[field],sort_keys=True) for r in mm for q in rows(ROOT/r['source_folder']/'requests.jsonl.gz')}
            assert len(values)==1,(game,field,values)
            params[field]=json.loads(next(iter(values)))
        fairness.append(dict(game=game,same_exact_initial_physical_state=True,initial_hash=mm[0]['initial_state_hash'],
            environment_commit=ENGINE_COMMIT,action_cap=300,full_quest_complete=[r['full_quest_complete'] for r in mm],
            same_initial_observation_and_history=True,verified_common_model_parameters=params,
            old_baselines_not_rerun=True,different_policy_prompts_by_design=True,
            stage24_authorized_continuation=game!='metropolis'))
    write(RESULTS/'comparison_fairness.json',fairness)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(3,2,figsize=(12,8),layout='constrained')
    for i,game in enumerate(GAMES):
        for method,color in [('Stage18-Fixed','#777777'),('AGC','#dd8535'),('AGC-v2','#287bb4')]:
            data=rows(RESULTS/'step_metrics'/f'{game}__{method}.jsonl.gz')
            axs[i,0].step([0]+[r['step'] for r in data],[0]+[r['quest'] for r in data],where='post',color=color,label=method)
            if method=='AGC-v2':
                axs[i,1].plot([r['step'] for r in data],[r['confidence'] for r in data],color=color,lw=1)
                metric=next(m for m in metrics if m['game']==game and m['method']==method)
                resets=metric['reset_windows']
                axs[i,1].plot([r['step'] for r in resets],[.02]*len(resets),'|',color='#b84a43',ms=5,label='Goal replacement')
        axs[i,0].set(title=game+' | main reward',xlim=(0,300),ylabel='Reward')
        axs[i,1].axhline(.4,color='#b84a43',ls='--',lw=1,label='Threshold 0.4')
        axs[i,1].set(title=game+' | confidence after action',xlim=(0,300),ylim=(-.02,1.03),ylabel='Heuristic confidence')
        for a in axs[i]:a.grid(alpha=.2);a.set_xlabel('Environment action')
    axs[0,0].legend(fontsize=8);axs[0,1].legend(fontsize=8,loc='upper right')
    fig.suptitle('Stage25: one seed42 trajectory per game; no statistical significance claim')
    figures=REPORTS/'figures';figures.mkdir(exist_ok=True)
    fig.savefig(figures/'confidence_and_reward.png',dpi=180);fig.savefig(figures/'confidence_and_reward.pdf');plt.close(fig)
    print(json.dumps(dict(indexed_steps=len(evidence),fair_initial_states=True,new_model_calls=0)))


if __name__=='__main__':main()
