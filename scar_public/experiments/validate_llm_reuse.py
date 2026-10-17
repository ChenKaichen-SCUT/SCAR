"""Post-run shadow checks of every LLM proposal veto, never fed back to the agent."""
import argparse
import json
from pathlib import Path

from scar.environment import AGENT_ID,restore
from scar_public.resource_trial import fresh,public_outcome
from scar_public.experiments.replay_real_reuse import execute


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    run=a.root/'runtime/llm_reuse/evidence_decision_v10/metropolis'
    manifest=json.loads((run/'manifest.json').read_text())
    current=json.loads((run/'current.json').read_text());assert current['complete']
    result=dict(agent_receives_validation_results=False,api_calls=0,checks=[])
    for path in sorted((run/'trace').glob('*.json')):
        row=json.loads(path.read_text());response=json.loads(row['response'])
        review=response.get('guarded_evidence_review')
        if not review:continue
        step=row['step'];prior=step-1
        cp=(Path(manifest['diagnostic_fork']['path']) if prior==184 else run/'checkpoints'/f'{prior:04d}')
        out=a.output/str(step);out.mkdir();env=restore(cp/'environment.pkl',out)
        before=env.obs[AGENT_ID]['text'];assert before==row['observation']
        scores=json.loads(json.dumps(env.scores))
        after,done=execute(env,review['action'])
        result['checks'].append(dict(step=step,vetoed=review['action'],executed=row['action'],
            actual_veto_status=public_outcome(after,review['action']),
            same_public_physical_state=fresh(before)==fresh(after),same_scores=scores==env.scores,
            actual_replacement_status=public_outcome(row['next_observation'],row['action']),
            observation=before,shadow_observation=after))
    result.update(validation_environment_actions=len(result['checks']),
        all_vetoes_failed_without_visible_progress=all(r['actual_veto_status']=='failure' and
            r['same_public_physical_state'] and r['same_scores'] for r in result['checks']))
    (a.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}))


if __name__=='__main__':main()
