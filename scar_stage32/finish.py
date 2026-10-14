"""Zero-API completion pipeline: verify, report, audit, commit and publish."""
import datetime,os,subprocess,sys,time,traceback
from .common import *

def main():
    # This process never invokes a model runner. It waits for the already launched batch.
    status=RUNTIME/'finalization.json';started=time.time()
    def note(phase,**kw):
        write(status,dict(phase=phase,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**kw));print(phase,flush=True)
    def command(args,log=None):
        if log:
            with (RUNTIME/log).open('w') as f:subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
        else:subprocess.run(args,cwd=ROOT,check=True)
    try:
        note('waiting_for_existing_online_batch')
        while not (RESULTS/'online_completion.json').exists():
            if time.time()-started>24*3600:raise RuntimeError('Existing online batch did not finish within 24 hours; no rerun launched')
            time.sleep(30)
        assert read(RESULTS/'online_completion.json')['complete'],'Existing batch reported an error; retain all states, no rerun'
        modules=['verify','analyze','cases','report','validate_analysis','audit']
        for name in modules:
            note(name);command([sys.executable,'-m','scar_stage32.'+name],f'{name}.log')
        note('commit_results');manifest=read(RESULTS/'artifact_manifest.json')['files'];paths=list(manifest)+['results/stage32/artifact_manifest.json','results/stage32/artifact_audit.json']
        # Explicit files avoid uploading __pycache__, runtime, dependencies or credentials.
        for i in range(0,len(paths),100):command(['git','add','-f','--',*paths[i:i+100]])
        command(['git','diff','--cached','--check'])
        if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:command(['git','commit','-m','stage32: report all SAER runs with exact replay and local counterfactual audit'])
        result_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();cost=read(RESULTS/'cost_reconciliation.json');conclusion=read(RESULTS/'conclusion.json')
        counts=[]
        for line in subprocess.check_output(['git','diff','--numstat',BASE,result_commit,'--','agents/saer','scar_stage32','reports/stage32','results/stage32'],cwd=ROOT,text=True).splitlines():
            added,deleted,path=line.split('\t',2);counts.append(dict(path=path,added=int(added) if added.isdigit() else None,deleted=int(deleted) if deleted.isdigit() else None))
        commits=[dict(hash=h,subject=s) for h,s in (line.split('\t',1) for line in subprocess.check_output(['git','log','--reverse','--format=%H%x09%s',f'{BASE}..{result_commit}'],cwd=ROOT,text=True).splitlines())]
        freeze_commit=read(RESULTS/'artifact_audit.json')['freeze_commit']
        write(RESULTS/'change_accounting.json',dict(base=BASE,freeze=freeze_commit,results=result_commit,commits=commits,files=counts,
            files_count=len(counts),added=sum(x['added'] or 0 for x in counts),deleted=sum(x['deleted'] or 0 for x in counts),metadata_self_excluded=True,
            new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],old_algorithm_files_changed=0,post_freeze_policy_changes=0,new_analysis_model_calls=0))
        write(RESULTS/'publication.json',dict(result_commit=result_commit,freeze_commit=freeze_commit,verdict=conclusion['verdict'],
            results_complete=True,all_validation_passed=True,new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],publication_commit_self_excluded=True))
        from scar_stage31.report import save,table
        save(REPORTS/'Git变更记录.md',f'''# Stage32 Git 与变更记录

本次修复前提交 `{BASE}`，修复后冻结 `{freeze_commit}`，完整单种子结果 `{result_commit}`。

{table(['提交','说明'],[[x['hash'],x['subject']] for x in commits])}

截至结果提交，共{len(counts)}个文件；文本新增{sum(x['added'] or 0 for x in counts)}行、删除{sum(x['deleted'] or 0 for x in counts)}行，二进制不计行数。逐文件统计见results/stage32/change_accounting.json；本元数据提交不包含自身哈希/行数，避免循环引用。

修复后新增模型请求{cost['new_requests']}次，usage费用${cost['cost_usd']:.9f}。分析与验证新增调用0。原AGC-v2、模型、环境不变，修复后冻结策略未再修改。正式记录只有seed42一次300步上限运行，修复后没有重跑。用户要求删除的旧Stage32结果已从当前版本移除，不混入本次统计。仅提交自研代码、报告和实验归档，没有下载依赖或凭据。
''')
        command(['git','add','--','results/stage32/change_accounting.json','results/stage32/publication.json','reports/stage32/Git变更记录.md'])
        command(['git','commit','-m','stage32: record result provenance and usage accounting'])
        note('push');command(['git','push','origin','main'])
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT,text=True).split()[0];assert head==remote
        tracked=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True);assert not tracked
        progress=ROOT.parent/'research-progress.json';d=read(progress);stage=d.setdefault('stage32',{})
        if not stage.get('cost_included_in_cumulative'):d['cumulative_cost_usd']=d.get('cumulative_cost_usd',0)+cost['cost_usd']
        stage.update(status='complete',commit=head,results_commit=result_commit,verdict=conclusion['verdict'],new_requests=cost['new_requests'],cost_usd=cost['cost_usd'],
            cost_included_in_cumulative=True,verification_passed=True,github_pushed=True,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        d.update(phase='stage32_complete',latest_commit=head);write(progress,d);note('complete',commit=head,results_commit=result_commit,cost_usd=cost['cost_usd'],verdict=conclusion['verdict'])
    except Exception as exc:
        note('stopped_for_review',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc());raise

if __name__=='__main__':main()
