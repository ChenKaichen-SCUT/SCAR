"""Prediction audit on observed data; never run a planner or fill censored labels."""
import argparse,json
from collections import Counter
from pathlib import Path
from statistics import median,mean
from math import log

BASE=Path(__file__).parent/'results'
ROOT=BASE/'2026-10-16-online-prediction'
OLD=BASE/'2026-10-16-resource-validation'
DONE={'PLAN_FOUND','NO_STRONG_POLICY_WITHIN_H'}


def errors(rows):
    complete=[r for r in rows if r.get('actual_remaining_units',0)>0 and not r.get('gated')]
    def one(key):
        ratios=[r[key]/r['actual_remaining_units'] for r in complete]
        return dict(pairs=len(ratios),median_predicted_over_actual=median(ratios) if ratios else None,
            median_multiplicative_error=median(max(x,1/x) for x in ratios) if ratios else None,
            mean_abs_log_error=mean(abs(log(x)) for x in ratios) if ratios else None,
            within_factor2=sum(.5<=x<=2 for x in ratios),within_factor10=sum(.1<=x<=10 for x in ratios))
    return dict(learned=one('predicted_units'),old_spine=one('old_spine'),
        censored=sum('work_observed_lower' in r for r in rows))


def calibration(rows,label,prob):
    known=[r for r in rows if r.get(label) is not None and not r.get('frame_censored')]
    if not known:return dict(n=0)
    bins=[]
    for i in range(5):
        group=[r for r in known if min(4,int(r[prob]*5))==i]
        if group:bins.append(dict(low=i/5,high=(i+1)/5,n=len(group),
            predicted=mean(r[prob] for r in group),observed=mean(int(r[label]) for r in group)))
    return dict(n=len(known),positives=sum(bool(r[label]) for r in known),
        brier=mean((r[prob]-int(r[label]))**2 for r in known),
        zero_brier=mean(int(r[label]) for r in known),bins=bins)


def lifetimes(rows):
    known=[r for r in rows if r.get('frame_censored') is False and r.get('residual_expansions',0)>0]
    pairs=[r for r in known if r.get('remaining_expansions_median') is not None]
    ratios=[max(1,r['remaining_expansions_median'])/r['residual_expansions'] for r in pairs]
    return dict(natural_exits=len(known),median_identified=len(pairs),unidentified=len(known)-len(pairs),
        median_predicted_over_actual=median(ratios) if ratios else None,
        median_multiplicative_error=median(max(x,1/x) for x in ratios) if ratios else None,
        within_factor2=sum(.5<=x<=2 for x in ratios))


def main():
    global ROOT
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT)
    ROOT=parser.parse_args().output
    if (ROOT/'analysis.json').exists():
        original=json.loads((ROOT/'analysis.json').read_text())['rows'];rows=[];forecasts=[]
        for r in original:
            stats=r.get('statistics') or {};p=stats.get('prediction') or {};f=stats.get('frontier') or {}
            row={k:r.get(k) for k in ('config','mode','status','value','verified_policy_depth','total_seconds',
                                      'parse_seconds','construct_seconds','search_seconds','timed_out')}
            row.update(expanded=stats.get('search_expanded'),optional_seconds=f.get('seconds'),
                prunes=f.get('prunes',0),prediction={k:v for k,v in p.items() if k not in ('forecasts','queries')},
                queries=p.get('queries',[]));rows.append(row)
            for q in p.get('forecasts',[]):
                entry={k:v for k,v in q.items() if k!='cost'}
                entry.update(id=r['config']['id'],mode=r['mode'],predicted_units=q['cost']['median'],
                    old_spine=max(1,q['cost']['old_spine']),fallback=q['cost']['fallback'],
                    cost_samples=q['cost']['samples'])
                forecasts.append(entry)
    else:
        rows=json.loads((ROOT/'runs_summary.json').read_text())['rows']
        forecasts=json.loads((ROOT/'forecasts.json').read_text())
    baseline=json.loads((OLD/'analysis.json').read_text())['rows']
    leaf={r['config']['id']:r for r in baseline if r['mode']=='leaf'}
    audit=json.loads((OLD/'source_audit.json').read_text())
    excluded={name for group in audit['groups'].values() for name in group[1:]}
    methods={}
    for mode in sorted({r['mode'] for r in rows}):
        group=[r for r in rows if r['mode']==mode]
        for r in group:
            b=leaf[r['config']['id']]
            if r['status'] in DONE and b['status'] in DONE:
                assert r['value']==b['value']
                if mode=='forecast_shadow':assert r['expanded']==b['statistics']['search_expanded']
            if r['status']=='PLAN_FOUND':assert r['verified_policy_depth']==r['value']
        methods[mode]=dict(status=dict(Counter(r['status'] for r in group)),
            deduplicated_status=dict(Counter(r['status'] for r in group if r['config'].get('folder') not in excluded)),
            prunes=sum(r['prunes'] for r in group),gate_skips=sum(r['prediction'].get('gate_skips',0) for r in group),
            prediction_log_dropped=sum(r['prediction'].get('prediction_log_dropped',0) for r in group))
    shadow=[r for r in forecasts if r['mode']=='forecast_shadow']
    first={}
    for r in shadow:first.setdefault((r['id'],r['query']),r)
    first=list(first.values())
    continued=[r for r in shadow if r['work_spent']>0]
    first_continued={}
    for r in continued:first_continued.setdefault((r['id'],r['query']),r)
    supported=[r for r in shadow if r['lifetime_samples']>=16]
    prediction={}
    for name,group in [('shadow_all',shadow),('shadow_first_per_query',first),
                       ('shadow_continuations',continued),
                       ('shadow_first_continuation_per_query',list(first_continued.values())),
                       ('shadow_lifetime_supported',supported)]:
        prediction[name]=dict(cost=errors(group),lifetime=lifetimes(group),
            timely_completion=calibration(group,'timely_completed','probability'),
            timely_rejection=calibration(group,'timely_rejected','timely_rejection_probability'))
    comparisons=[]
    for r in baseline:
        if r['config']['family']=='rovers' and r['mode'] in ('leaf','amortized_relation'):
            comparisons.append(dict(config=r['config'],mode=r['mode'],status=r['status'],
                expanded=r.get('statistics',{}).get('search_expanded'),total_seconds=r.get('total_seconds')))
    previous=json.loads((BASE/'2026-10-16-frontier-scheduler/runs_summary.json').read_text())['rows']
    for r in previous:
        if r['config']['family']=='rovers' and r['mode']=='focus_priority':
            comparisons.append({k:r[k] for k in ('config','mode','status','expanded','total_seconds')})
    comparisons += [{k:v for k,v in r.items() if k!='queries'} for r in rows if r['config']['family']=='rovers']
    summary=dict(scope=f'{len(rows)} new-variant development runs on50 observed configs,46 distinct. No baseline reruns. Predictors reset per instance; predictions precede outcomes. Shadow does not prune. Single measurements; no independent holdout or formal calibration guarantee.',
        methods=methods,prediction=prediction,rover_comparison=comparisons,api_calls=0)
    (ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'runs_summary.json').write_text(json.dumps(dict(rows=rows),separators=(',',':')),encoding='utf-8')
    (ROOT/'forecasts.json').write_text(json.dumps(forecasts,separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(methods=methods,prediction=prediction),indent=2))


if __name__=='__main__':main()
