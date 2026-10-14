"""Exhaustive branch evidence and publication-ready diagnostic figures."""
from collections import Counter
from agents.agc.state import extract
from .common import *

def main():
    offline();check_freeze();source=rows(SOURCE/'trajectory.jsonl.gz');metrics=read(RESULTS/'paired_metrics.json')
    lookup={(m['start'],m['variant']):m for m in metrics};diagnostics=[];anomalies=[]
    for n in CASES:
        folder=RESULTS/'runs'/case_id(n)/'Oracle';rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz')
        m=lookup[n,'Oracle'];original=lookup[n,'Original'];first=rr[0];base=source[n-1];retry=[]
        for r in rr:
            if r['decision']['action_retry_calls']:
                retry.append(dict(step=r['step'],proposals=[dict(action=(a['proposal'] or {}).get('action'),hard=a['hard'],reasons=a['reasons'],executed=a['executed']) for a in r['decision']['attempts']],
                    executed_action=r['action'],feedback=extract(r['feedback'])['feedback']))
        for i,q in enumerate(qq):
            issues=[];raw=q.get('raw_response',{});parsed=q.get('parsed_json')
            if q['status']!='ok':issues.append(q['status'])
            if q.get('parse_exception'):issues.append(q['parse_exception'])
            if raw and raw['choices'][0]['finish_reason']!='stop':issues.append('finish:'+raw['choices'][0]['finish_reason'])
            if not isinstance(parsed,dict) or not isinstance(parsed.get('action'),str):issues.append('missing_action')
            if issues:anomalies.append(dict(case=case_id(n),step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],line=i+1,issues=issues))
        terminal=read(folder/'decision_exhausted.json') if (folder/'decision_exhausted.json').exists() else None
        first_delta=dict(original_action=base['action'],oracle_action=first['action'],original_feedback=extract(base['feedback'])['feedback'],oracle_feedback=extract(first['feedback'])['feedback'],
            original_public_failed=original['first_action']['public_failed'],oracle_public_failed=m['first_action']['public_failed'],
            original_public_informative=original['first_action']['public_progress']['informative'],oracle_public_informative=m['first_action']['public_progress']['informative'],
            original_hp_after=original['first_action']['hp_after'],oracle_hp_after=m['first_action']['hp_after'],
            original_main_delta=original['first_action']['main_delta'],oracle_main_delta=m['first_action']['main_delta'],
            same_pre_action_state=base['state_hash_before']==first['state_hash_before'],
            same_model_decision=base['decision']==first['decision'])
        assert first_delta['same_pre_action_state'] and first_delta['same_model_decision']
        diagnostics.append(dict(case=case_id(n),start=n,first_step=first_delta,
            original_next5=[dict(step=r['step'],action=r['action'],feedback=extract(r['feedback'])['feedback'].split('\n')[0]) for r in source[n:n+5]],
            oracle_next5=[dict(step=r['step'],action=r['action'],feedback=extract(r['feedback'])['feedback'].split('\n')[0]) for r in rr[1:6]],
            action_retry_decisions=retry,terminal_rejection=terminal,
            longest_goals=sorted(m['goal_segments'],key=lambda g:g['end']-g['start'],reverse=True)[:3],
            action_verbs=dict(Counter(r['action'].split()[0] for r in rr)),
            no_main_gain_after_last_milestone=m['tail_without_main_progress'],oracle_final_goal=rr[-1]['control_after']['goal']))
    write(RESULTS/'diagnostics.json',diagnostics);write(RESULTS/'response_anomalies.json',anomalies)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    figures=REPORTS/'figures';figures.mkdir(exist_ok=True)
    failures=read(RESULTS/'source_failure_statistics.json')
    fig,axs=plt.subplots(3,1,figsize=(12,7),sharex=True,layout='constrained')
    xx=[r['step'] for r in source]
    axs[0].step(xx,[r['scores']['quest'] for r in source],where='post',color='#287bb4');axs[0].set(ylabel='Main reward',ylim=(-.05,1.2))
    axs[0].axvspan(39,300,color='#dedede',alpha=.5);axs[0].text(100,.5,'261 actions after last main progress',fontsize=10)
    axs[1].scatter([r['step'] for r in failures['failed_actions']],[1]*len(failures['failed_actions']),marker='x',color='#b84a43',label='B: native public rejection')
    axs[1].scatter([r['step'] for r in failures['rejected_proposals']],[2]*len(failures['rejected_proposals']),marker='^',color='#dd8535',label='A: filtered model proposal')
    axs[1].scatter(list(CASES),[0]*len(CASES),marker='|',s=100,color='#287bb4',label='Oracle checkpoint')
    axs[1].set(yticks=[0,1,2],yticklabels=['Selected','Executed failure','Filtered format'],ylim=(-.5,2.8));axs[1].legend(fontsize=8,ncol=3,loc='upper left')
    axs[2].plot(xx,[r['control_after']['goal']['confidence'] for r in source],lw=1,color='#287bb4');axs[2].axhline(.4,ls='--',color='#b84a43',lw=1)
    axs[2].set(ylabel='Goal confidence',xlabel='Original environment action',xlim=(0,300),ylim=(0,1.05))
    for ax in axs:ax.grid(alpha=.2)
    fig.suptitle('Stage26: one Stage25 remnant parent trajectory; A/B counts have different denominators')
    fig.savefig(figures/'original_failure_timeline.png',dpi=180);fig.savefig(figures/'original_failure_timeline.pdf');plt.close(fig)
    fig,axs=plt.subplots(5,2,figsize=(12,13),sharex=True,sharey=True,layout='constrained')
    upper=max([1]+[m['main'] for m in metrics])+1
    for ax,(n,case) in zip(axs.flat,CASES.items()):
        data=rows(RESULTS/'step_metrics'/f'{case_id(n)}__Oracle.jsonl.gz')
        ax.step(xx,[r['scores']['quest'] for r in source],where='post',color='#777777',label='Original (reused)')
        ax.step([n-1]+[r['step'] for r in data],[lookup[n,'Oracle']['main_before']]+[r['main'] for r in data],where='post',color='#287bb4',label='One-action Oracle')
        ax.axvline(n,color='#dd8535',ls=':',lw=1);ax.set(title=f'a{n}: {case["action"]}',xlim=(0,300),ylim=(-.05,upper),ylabel='Main reward');ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=8);axs[-1,0].set_xlabel('Absolute environment action');axs[-1,1].set_xlabel('Absolute environment action')
    fig.suptitle('Ten dependent checkpoints, one parent; no significance claim')
    fig.savefig(figures/'paired_main_progress.png',dpi=180);fig.savefig(figures/'paired_main_progress.pdf');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained');indices=np.arange(10);labels=[str(n) for n in CASES]
    for v,offset,color in [('Original',-.18,'#888888'),('Oracle',.18,'#287bb4')]:
        axs[0].bar(indices+offset,[lookup[n,v]['windows']['following20']['new_states'] for n in CASES],.36,label=v,color=color)
        axs[1].bar(indices+offset,[lookup[n,v]['windows']['following20']['failures'] for n in CASES],.36,label=v,color=color)
    for ax,title in zip(axs,['New public states, next 20 actions','Rejected environment actions, next 20 actions']):
        ax.set(title=title,xticks=indices,xticklabels=labels,xlabel='Intervention at original action');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Excludes the corrected action; truncated windows retain actual counts')
    fig.savefig(figures/'short_term_comparison.png',dpi=180);fig.savefig(figures/'short_term_comparison.pdf');plt.close(fig)
    print(json.dumps(dict(cases=len(diagnostics),response_anomalies=len(anomalies),new_model_calls=0)))

if __name__=='__main__':main()
