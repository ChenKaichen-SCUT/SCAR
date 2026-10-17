"""Reproduce comparison tables from the published public records; zero API calls."""
import argparse
import json
from pathlib import Path
import tarfile

from scar_public.resource_trial import public_outcome


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();root=a.directory
    data=json.loads((root/'llm_results.json').read_text(encoding='utf-8'))
    checks=json.loads((root/'llm_veto_checks.json').read_text(encoding='utf-8'))
    frozen=json.loads((root/'frozen_summary.json').read_text(encoding='utf-8'))
    threshold=min(r['current']['scores']['quest'] for r in data['arms'])
    table=[]
    with tarfile.open(root/'public_evidence.tgz') as archive:
        for arm in data['arms']:
            prefix='runtime/llm_'+arm['arm']+'/evidence_decision_v10/metropolis/'
            rows=[json.load(archive.extractfile(m)) for m in archive.getmembers()
                  if m.name.startswith(prefix+'trace/')]
            rows.sort(key=lambda r:r['step'])
            reached=next(r['step'] for r in rows if r['scores']['quest']>=threshold)
            audits=[json.loads(l) for l in archive.extractfile(prefix+'api/attempts.jsonl').read().decode().splitlines()]
            earlier=[r for r in audits if r['step']<reached]
            completed=[r for r in earlier if r['event']=='completed']
            table.append(dict(arm=arm['arm'],final_score=arm['current']['scores']['quest'],
                full_task_completed=arm['current']['termination']=='environment',
                actions_with_acquisition=arm['total_actions_including_acquisition'],
                gavel_failed_attempts=sum(public_outcome(r['feedback'],r['action'])=='failure' for r in arm['gavel_attempts']),
                guarded_repairs=len(arm['reviews']),api_requests=arm['current']['usage']['requests'],
                peak_usd_estimate=arm['current']['usage']['peak_usd_estimate'],
                summed_request_seconds=arm['current']['usage']['summed_request_seconds'],
                common_score=threshold,first_reached_step=reached,
                actions_to_common_score_with_acquisition=reached-183,
                requests_to_common_score=sum(r['event']=='started' for r in earlier),
                peak_usd_to_common_score=sum(r.get('peak_usd',0) for r in completed),
                request_seconds_to_common_score=sum(r['elapsed_s'] for r in completed)))
    report=dict(primary_endpoint='Score at the absolute 300-action budget; one sample per arm',
        secondary_threshold='Post-hoc descriptive highest common score, not a preregistered endpoint',
        initial_requests_identical=data['same_initial_request'],llm_comparison=table,
        frozen_stream=frozen,vetoes_validated=checks['validation_environment_actions'],
        all_llm_vetoes_validated=checks['all_vetoes_failed_without_visible_progress'],
        total_api_requests=data['total_api_requests'],unknown_charge_attempts=data['unknown_charge_attempts'],
        configured_peak_usd_estimate=data['configured_peak_usd_estimate'])
    shared=root/'shared_acquisition_api.json'
    if shared.exists():
        report['previously_billed_shared_acquisition']=json.loads(shared.read_text(encoding='utf-8'))
        report['api_table_scope']='New calls after checkpoint 0184; shared historical prefix is not billed again'
    (root/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
