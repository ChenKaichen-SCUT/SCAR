import hashlib,json,os
from collections import Counter
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');rid='remnant__v3r6_300_20261019'
def rows(p):
    out=[]
    if p.exists():
        for line in p.read_text().splitlines():
            try:out.append(json.loads(line))
            except json.JSONDecodeError:pass
    return out
status=json.loads((R/'feedback_v3r6_300_status.json').read_text());protocol=json.loads((R/'feedback_v3r6_300_protocol.json').read_text())
run=status['runs'][rid];log=rows(R/'runs'/rid/'agent_adam_davis/agent_log.jsonl');audit=rows(R/'control_audit'/(rid+'.jsonl'));api=rows(R/'telemetry'/rid/'api_calls.jsonl')
decisions=[x for x in audit if x.get('event')=='decision'];loaded=[x for x in audit if x.get('event')=='policy_loaded']
proc=Path('/proc')/str(run.get('pid',-1));cmd=(proc/'cmdline').read_bytes().decode().replace('\0',' ') if (proc/'cmdline').exists() else None
sources={n:hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in protocol['source_sha256'].items()}
protected={n:hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in protocol['previous_artifacts_preserved_sha256'].items()}
out={'phase':status['phase'],'run_status':run,'steps':len(log),'main_quest':sum(x['reward'].get('quest',0) for x in log),'last_gain_step':max([r['step']+1 for r in log if r['reward'].get('quest',0)>0],default=0),
 'completed_api_calls':sum(x.get('event')=='completed' for x in api),'api_errors_or_stops':[x for x in api if x.get('event') not in ['started','completed']],
 'policy_loaded':loaded,'process_command':cmd,'source_hashes_match':all(sources.values()),'old_artifacts_unchanged':all(protected.values()),
 'dispatch_sources':dict(Counter(x['dispatch']['source'] for x in decisions)),'latest_mechanisms':decisions[-1]['packet'].get('v3r4_mechanisms') if decisions else None,
 'recent_actions':[{'step':x['step']+1,'action':x['action']} for x in log[-5:]],'report_ready':(R/'feedback_v3r6_300_analysis.json').exists()}
(R/'feedback_v3r6_300_progress.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
