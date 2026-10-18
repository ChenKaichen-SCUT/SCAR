"""All original soft diagnoses in two specified old development runs.

Original requests must be exact cache hits. New evidence judgments are not
independent replications and cannot be used as game-performance evidence.
"""
import argparse,contextlib,json,sys
from pathlib import Path

from scar.environment import restore
from scar.io import atomic_json
from scar_public.experiments.continuation_branch import ReusingProvider
from scar_public.experiments.sentry_foundation_trial import system_prompt
from scar_public.provider import usage_summary
from scar_public.sentry_evidence import OutcomeLedger,EvidenceJudge


def main():
    p=argparse.ArgumentParser();p.add_argument('--block',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--key',required=True);a=p.parse_args()
    from Sentry.models import LocalTraceWindow,TaskContext,agent_step_from_parts
    from Sentry.detector import build_detector_prompt,parse_detector_response
    events=[json.loads(s) for s in (a.block/'sentry_events.jsonl').read_text().splitlines()]
    provider=ReusingProvider(a.out/'api',a.key,historical=a.block/'api');provider.arm='evidence_probe'
    with contextlib.redirect_stdout(sys.stderr):system=system_prompt(restore(a.block/'initial.pkl'),provider.model)
    task=TaskContext(objective=events[0]['objective'],action_schema=system)
    ledger=OutcomeLedger();window=LocalTraceWindow(max_size=5);old=EvidenceJudge(provider,ledger,False);new=EvidenceJudge(provider,ledger,True)
    results=[];latest=None
    for event in events:
        if event['type']=='agent_step':
            s=event['step'];latest=s['step_id'];act=s['action']['raw'];obs=s['observation']
            ledger.add(latest,act,obs)
            window.add(agent_step_from_parts(step_id=latest,reasoning=s['reasoning'],raw_action=act,
                tool_name='game',tool_args={'command':act},observation=obs,accepted_by_environment=None))
            new.query=s['reasoning']+'\n'+act+'\n'+obs;new.before=latest-4
        if event['type']!='rescue_injected' or event['route']!='soft_repair':continue
        provider.step=latest;prompt=build_detector_prompt(window,task)
        provider.cache_only=True;original=old(prompt,temperature=0.0,max_tokens=4096,response_format={'type':'json_object'})
        assert parse_detector_response(original).should_rescue
        provider.cache_only=False;changed=new(prompt,temperature=0.0,max_tokens=4096,response_format={'type':'json_object'})
        selected=ledger.retrieve(new.query,new.before)
        row=dict(cycle=latest,original=json.loads(original),evidence=json.loads(changed),
            historical_records=selected,qualification='Same public current window; only additional historical evidence differs')
        results.append(row);atomic_json(a.out/'current.json',dict(completed=len(results),latest_cycle=latest))
    atomic_json(a.out/'result.json',dict(rows=results,usage=usage_summary(a.out/'api'),
        qualification='Selected old SCAR-prompt/Sentry trajectories; no environment actions or score inference'))
    print(json.dumps(dict(completed=len(results),usage=usage_summary(a.out/'api'))))


if __name__=='__main__':main()
