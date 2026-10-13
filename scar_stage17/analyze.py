"""Pre-frozen descriptive analysis. Missing/aborted runs remain in denominator."""
import csv
import json
import math
import statistics as st
from collections import Counter,defaultdict
from pathlib import Path
from .common import ROOT,RESULTS,METHODS,load,write,read_gzip
from scar.providers.deepseek import estimate_cost
from .provider import CONFIG
from scar_v3.state import parse_action
from scar.agents.scar.state import feedback_text

NAMES={'A0':'SCAR S1+P1+P3 (100步预算适配)','A1':'ReAct + STM5','A2':'LongContext','A3':'AdaPlanner-AgentOdyssey Adaptation','A4':'Deterministic DAG'}


def mean(values):return st.mean(values) if values else None

def wilson(k,n):
    z=1.96;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]


def knowledge_stats(task,truth,rows,requests):
    graph=truth['recipes'];names={oid:r['name'] for oid,r in graph.items()}
    def coverage(facts):
        relation=[];quantity=[];station=[];full=[]
        for oid,rule in graph.items():
            f=facts.get(rule['name'],{})
            # Internal names may differ from object IDs. Evaluator stores its own mapping.
            expected=rule.get('ingredient_names',{})
            rel=bool(f.get('ingredients')) and set(f['ingredients'])==set(expected)
            qty=rel and f.get('quantities')==expected
            req=set(rule.get('station_names',[]));sta=req.issubset(set(f.get('stations') or []))
            if rel:relation.append(rule['name'])
            if qty:quantity.append(rule['name'])
            if sta:station.append(rule['name'])
            if qty and sta:full.append(rule['name'])
        return dict(relation=relation,quantity=quantity,station=station,full=full)
    initial=coverage(rows[0]['public_knowledge_before']) if rows else coverage({})
    final=coverage(rows[-1]['public_knowledge_after']) if rows else initial
    first={};used={};complete=0 if len(initial['full'])==len(graph) else None;internal_missed={};context_evidence={}
    for row in rows:
        c=coverage(row['public_knowledge_after'])
        if len(c['full'])==len(graph) and complete is None:complete=row['step']
        for name in c['quantity']:first.setdefault(name,row['step'])
        for oid,count in row['metrics']['actual_production'].items():
            if oid in names and count>0:used.setdefault(names[oid],row['step'])
        decision=row['decision'];facts=decision.get('controller',{}).get('table',decision.get('table',{})).get('knowledge',{}).get('facts')
        if facts is not None:
            missing=sorted(set(row['public_knowledge_before'])-set(facts))
            if missing:internal_missed[str(row['step'])]=missing
        # Text availability is not evidence that an LLM understood or applied a rule.
        messages='\n'.join(m['content'] for request in requests if request['step']==row['step'] for m in request['messages'])
        if messages:
            available=[name for name,f in row['public_knowledge_before'].items() if f.get('raw_evidence') and f['raw_evidence'] in messages]
            context_evidence[str(row['step'])]=available
    for name in initial['quantity']:first[name]=0
    latencies={name:used[name]-first[name] for name in first.keys()&used.keys() if used[name]>=first[name]}
    return dict(closure_size=len(graph),initial=initial,final=final,first_full_closure_step=complete,
        first_quantity_discovery=first,first_successful_craft=used,knowledge_to_craft_latency=latencies,
        missing_final_relations=sorted(set(names.values())-set(final['relation'])),
        missing_final_quantities=sorted(set(names.values())-set(final['quantity'])),
        missing_final_stations=sorted(set(names.values())-set(final['station'])),
        observed_not_registered=internal_missed,raw_evidence_in_current_request=context_evidence,
        limitation='Static dependency closure includes bypassable naturally available intermediates. Coverage is explanatory, not proof of unavoidable knowledge; raw text availability does not establish model understanding.')


def row_stats(task,method,truth):
    path=RESULTS/'runs'/f"{task['task_id']}__{method}"
    if not (path/'summary.json').exists():return dict(task_id=task['task_id'],method=method,status='missing',success=False,steps=0,game=task['game_name'],depth=task['dependency_depth'])
    summary=load(path/'summary.json');rows=read_gzip(path/'trajectory.jsonl.gz');requests=read_gzip(path/'requests.jsonl.gz')
    kinds=Counter();inspects=Counter();inspect_feedback={};crafts=Counter();no_progress=longest=0
    for r in rows:
        m=r['metrics'];p=parse_action(r['action'])
        for k in ('invalid','craft_failed','material_rejection','station_rejection'):kinds[k]+=int(m[k])
        if p.verb=='inspect':
            text=feedback_text(r['feedback']['text'])
            kinds['identical_feedback_repeat_inspections']+=inspect_feedback.get(p.target)==text
            inspect_feedback[p.target]=text;inspects[p.target]+=1
        if p.verb=='craft' and m['actual_production']:crafts[p.target]+=1
        kinds['resource_loss_events']+=bool(m['unaccounted_resource_loss'])
        if r['knowledge_delta']['new_relations'] or r['knowledge_delta']['quantity_updates'] or m['actual_production'] or r['physical_after']['target_owned']>r['physical_before']['target_owned']:no_progress=0
        else:no_progress+=1;longest=max(longest,no_progress)
    tokens=Counter();cost=0
    for req in requests:
        usage=req.get('usage',{});tokens['input_tokens']+=usage.get('prompt_tokens',0);tokens['output_tokens']+=usage.get('completion_tokens',0)
        tokens['cache_hit_tokens']+=usage.get('prompt_cache_hit_tokens',0);cost+=req['charged_or_reserved_usd']
    knowledge=knowledge_stats(task,truth,rows,requests)
    made=max([r['target_produced_during_task'] for r in rows]+[0])
    result=dict(summary,game=task['game_name'],depth=task['dependency_depth'],family=task['family'],
        R60=bool(summary['success'] and summary['steps']<=60),R80=bool(summary['success'] and summary['steps']<=80),R100=bool(summary['success']),
        **dict(kinds),invalid_rate=kinds['invalid']/len(rows) if rows else 0,
        repeated_inspections=sum(max(0,v-1) for v in inspects.values()),
        repeated_successful_crafts=sum(max(0,v-1) for v in crafts.values()),
        repeat_scope='Repeated target names; may be necessary refreshes or legitimate batches, not automatically waste',
        longest_no_recorded_goal_progress=longest,target_made_not_obtained=bool(made and not summary['success']),
        api_calls=len(requests),api_failed_requests=sum(r['status']!='ok' for r in requests),
        api_phases=dict(Counter(r['phase'] for r in requests)),**dict(tokens),cost_usd=cost,
        peak_input_tokens=max([r.get('usage',{}).get('prompt_tokens',0) for r in requests]+[0]),knowledge=knowledge)
    if summary['success']:reason='成功'
    elif summary['status'] not in ('step_limit','game_failure'):reason='运行/API异常或中止'
    elif task['target_item'] in knowledge['missing_final_relations']:reason='目标配方关系尚未公开'
    elif task['target_item'] in knowledge['missing_final_quantities']:reason='目标材料数量尚未公开'
    elif result['target_made_not_obtained']:reason='已产出目标但未实际取得'
    elif knowledge['missing_final_relations'] or knowledge['missing_final_quantities']:reason='部分依赖闭包知识未公开；可能存在替代获取路径'
    else:reason='材料关系与数量已公开，仍有执行/站点/动作预算问题'
    result['descriptive_failure_category']=reason
    return result


def aggregate(rows):
    n=len(rows);s=[r['steps'] for r in rows if r['success']]
    result=dict(n=n,success=sum(r['success'] for r in rows),success_steps_mean=mean(s),success_steps_median=st.median(s) if s else None,
        success_steps=s,total_actions=sum(r['steps'] for r in rows),statuses=dict(Counter(r['status'] for r in rows)))
    for b in (60,80,100):result['R'+str(b)]=sum(r.get('R'+str(b),False) for r in rows)/n
    result['nominal_wilson_R100']=wilson(result['success'],n)
    for k in ('invalid','craft_failed','material_rejection','station_rejection','repeated_inspections','repeated_successful_crafts','resource_loss_events','identical_feedback_repeat_inspections','target_made_not_obtained','api_calls','api_failed_requests','input_tokens','output_tokens','cache_hit_tokens','cost_usd'):
        result[k]=sum(r.get(k,0) for r in rows)
    return result


def main():
    tasks=load(RESULTS/'tasks.json');truth=load(RESULTS/'evaluator_truth.json');rows=[row_stats(t,m,truth[t['task_id']]) for t in tasks for m in METHODS]
    summaries={m:aggregate([r for r in rows if r['method']==m]) for m in METHODS}
    pairs=[]
    for other in METHODS[1:]:
        differences=[]
        for task in tasks:
            a=next(r for r in rows if r['task_id']==task['task_id'] and r['method']=='A0')
            b=next(r for r in rows if r['task_id']==task['task_id'] and r['method']==other)
            differences.append(dict(task_id=task['task_id'],game=task['game_name'],delta=int(a['success'])-int(b['success']),
                action_delta=a['steps']-b['steps'],cost_delta=a.get('cost_usd',0)-b.get('cost_usd',0)))
        wins=sum(d['delta']>0 for d in differences);loss=sum(d['delta']<0 for d in differences);n=wins+loss
        p=min(1,2*sum(math.comb(n,k) for k in range(min(wins,loss)+1))/(2**n)) if n else 1
        pairs.append(dict(comparison='A0 vs '+other,wins=wins,losses=loss,ties=len(tasks)-n,
            exploratory_exact_mcnemar_p=p,limitations='One stochastic model sample; task correlations violate independent-pair interpretation.',tasks=differences))
    strata={}
    for key in ('game','depth','family'):
        strata[key]={str(value):{m:aggregate([r for r in rows if r[key]==value and r['method']==m]) for m in METHODS} for value in sorted({r[key] for r in rows})}
    write(RESULTS/'analysis.json',dict(methods=summaries,paired=pairs,strata=strata,complete=all(r['status']!='missing' for r in rows)))
    write(RESULTS/'per_task.json',rows)
    fields=['task_id','game','family','depth','method','status','success','steps','R60','R80','R100','craft_failed','invalid','repeated_inspections','api_calls','input_tokens','output_tokens','cost_usd','descriptive_failure_category']
    with (RESULTS/'per_task.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    reports=ROOT/'reports/stage17';reports.mkdir(parents=True,exist_ok=True)
    table='|方法|R@60|R@80|R@100|成功平均步数|制作失败|重复检查|输入/输出 tokens|费用 USD|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for m,s in summaries.items():
        avg='—' if s['success_steps_mean'] is None else f"{s['success_steps_mean']:.1f}"
        table+=f"|{NAMES[m]}|{s['R60']:.1%}|{s['R80']:.1%}|{s['R100']:.1%}|{avg}|{s['craft_failed']}|{s['repeated_inspections']}|{s['input_tokens']:,} / {s['output_tokens']:,}|{s['cost_usd']:.6f}|\n"
    (reports/'五算法性能对比.md').write_text('# 五算法性能对比\n\n'+table+'\n每种方法分母均为24，异常和中止保留。逐任务表见 `results/stage17/per_task.csv`，动作分布、名义 Wilson 区间、按游戏/深度/family 分层及配对变化见 `analysis.json`。重复检查仅为同一对象再次检查，不等于不必要检查。\n\n'+ '\n'.join(f"- {p['comparison']}: 胜 {p['wins']}、负 {p['losses']}、平 {p['ties']}；探索性配对检验 p={p['exploratory_exact_mcnemar_p']:.4g}。" for p in pairs)+'\n\n只有一次温度0.7模型采样，物理种子相同不表示模型回答配对。游戏和共享配方使任务相关；名义区间和检验不能视为可靠的独立样本推断，也不能证明模块因果收益。\n')
    lines=['# 规则知识发现与利用分析','', '同时保存客观公开证据和方法内部状态。A0/A4 的登记表可直接审计；A1/A2/A3 仅检验真实请求中出现的公开证据文本，不能据此声称模型理解了规则。所有离线解析结果不回注算法。','', '配方关系、数量、站点覆盖分别计算。站点集合由隐藏评测真值检查覆盖；算法本身仍可能只知道部分要求。静态依赖闭包含可由天然物品绕过的中间产物，因此闭包缺失是解释性指标，不应自动认定为失败的必要原因。']
    for m in METHODS:
        selected=[r for r in rows if r['method']==m and 'knowledge' in r]
        initial=mean([len(r['knowledge']['initial']['quantity'])/r['knowledge']['closure_size'] for r in selected]);final=mean([len(r['knowledge']['final']['quantity'])/r['knowledge']['closure_size'] for r in selected])
        fullfail=sum(not r['success'] and not r['knowledge']['missing_final_quantities'] and not r['knowledge']['missing_final_stations'] for r in selected)
        lines+=['',f"- {m}: 初始数量知识闭包覆盖均值 {initial or 0:.1%}，结束 {final or 0:.1%}；离线检验关系/数量/站点覆盖完整仍失败 {fullfail}/24。"]
    lines+=['','逐任务首次披露、完整闭包时刻、制作使用延迟、缺失知识、公开但未登记和每次请求中的证据列表见 `per_task.json`。首次制作早于显式数量披露的情况保留原时刻，不虚构正延迟。']
    (reports/'规则知识发现与利用分析.md').write_text('\n'.join(lines)+'\n')
    failures=['# 失败任务逐例分析','', '|任务|方法|状态/步数|描述性归因|缺失关系|缺失数量|缺失站点|','|---|---|---|---|---|---|---|']
    for r in rows:
        if not r['success']:
            k=r.get('knowledge',{});failures.append('|'+ '|'.join([r['task_id'],r['method'],r['status']+'/'+str(r['steps']),r.get('descriptive_failure_category','未运行'),', '.join(k.get('missing_final_relations',[])),', '.join(k.get('missing_final_quantities',[])),', '.join(k.get('missing_final_stations',[]))])+'|')
    failures+=['','上述分类是按预注册顺序生成的描述性标签，不能单凭最终知识缺失推断因果。原始动作、反馈、资源变化和请求见各 run 的压缩原始文件。']
    (reports/'失败任务逐例分析.md').write_text('\n'.join(failures)+'\n')
    total=sum(s['cost_usd'] for s in summaries.values())
    (reports/'费用与复现报告.md').write_text(f'# 费用与复现报告\n\n正式请求保守峰时协议计费合计 **${total:.6f}**。计价为每百万 tokens：缓存命中0.006、未命中0.3、输出1.2美元；这不是账户账单。未能确认用量的请求按预留上界单列计入。连通性检查费用单列在 `connectivity.json`。\n\n'+ '\n'.join(f"- {m}：{s['api_calls']} 次请求，${s['cost_usd']:.6f}，状态 {s['statuses']}。" for m,s in summaries.items())+'\n\n使用 Python 3.12、固定引擎版本并设置 AGENTODYSSEY_ROOT、PYTHONHASHSEED=0 和 OMP_NUM_THREADS=1。执行 `python -m scar_stage17.replay --site local --runtime /path/to/empty/replay` 可进行不调用API的原生重放；`python -m scar_stage17.analyze` 重建统计。正式复现需冻结版本和独立输出目录，不可覆盖本轮成绩。服务器部署与命令详见统一协议，版本见 sources.json。\n')
    conclusions=['# 实验总报告','',table,'',f'共24×5=120组；已归档 {sum(r["status"]!="missing" for r in rows)} 组。']
    for rq,other in [('RQ1','A1'),('RQ1','A2'),('RQ2','A3'),('RQ3','A4')]:
        delta=summaries['A0']['R100']-summaries[other]['R100'];cost=summaries['A0']['cost_usd']-summaries[other]['cost_usd']
        conclusions+=['',f'{rq}：A0 相对 {other} 的 R@100 差为 {delta:+.1%}，总协议费用差为 ${cost:+.6f}。这是本次任务集与单次采样下的描述，不是机制的因果证明。']
    conclusions+=['','RQ4：逐任务失败表按目标关系、数量、依赖闭包、产出未取得及运行异常记录；不能把所有失败都归于未知配方。需结合资源拒绝、站点反馈、实际消费和动作上限解释。','', '任务来自原生世界的自定义制作并持有目标，不能表述为官方主任务排行榜。15/9的游戏分布不均；结论仅覆盖robot_kingdom和quarantine，不能宣称对所有游戏普遍有效。所有任务共享游戏规则，且部分材料关系与旧阶段重叠；相关性和一次模型采样限制统计推断。','', '本轮结束后不调整冻结S1/P1/P3，不在正式测试集上开发未知规则模块。']
    (reports/'实验总报告.md').write_text('\n'.join(conclusions)+'\n')
    print(json.dumps({'complete':all(r['status']!='missing' for r in rows),'runs':len(rows),'cost_usd':total}))

if __name__=='__main__':main()
