"""Pre-online coverage on all 20 Stage29/30 recovery suffixes; no LLM calls."""
from collections import Counter
from agents.rec_v1.state import Tracker,failed,visible
from scar_stage28.common import CASES as CHECKPOINTS,selected
from .common import *

def sources():
    for ident in CHECKPOINTS:
        for variant,stage,folder in [('OriginalRecovery',28,'OracleRecovery'),('OracleGoalStack',30,'OracleGoalStack')]:
            yield ident,variant,ROOT/f'results/stage{stage}/runs/{ident}/{folder}/trajectory.jsonl.gz'

def initialize(ident):
    tracker=Tracker()
    prefix=json.loads(gzip.decompress((ROOT/f'results/stage27/checkpoints/{ident}/public_prefix.json.gz').read_bytes()))
    for r in prefix:tracker.observe(r['observation'],r['action'],r['feedback'])
    return tracker

def main():
    offline();out=[];trajectories=[]
    for ident,variant,path in sources():
        tracker=initialize(ident);rr=rows(path);n=0
        for line,r in enumerate(rr,1):
            tracker.ingest(r['observation']);prop=r['decision']['attempts'][-1]['proposal'];assert prop['action'].strip()==r['action']
            assessment=tracker.assess(prop);summary=tracker.summary(prop.get('goal_description',''))
            kinds=[x['kind'] for x in assessment['reasons']]
            observable=dict(actual_rejected=failed(r['feedback']),visibility_lost=visible(r['observation']) and not visible(r['feedback']) and 'too dark to see' in r['feedback']['text'].lower(),
                repeated_rejection_witness='unchanged_public_failure' in kinds and failed(r['feedback']),
                exact_task_harm_unknown=bool(set(kinds)&{'required_resource_custody_risk','facility_departure_risk'}))
            out.append(dict(id=ident,variant=variant,step=r['step'],source=str(path.relative_to(ROOT)),line=line,
                action=r['action'],goal=prop.get('goal_description'),reasoning=prop.get('reasoning'),assessment=assessment,
                public_state=summary,observed_outcome=observable,observation=r['observation'],feedback=r['feedback']))
            n+=assessment['decision']=='RECONSIDER'
            tracker.observe(r['observation'],r['action'],r['feedback'],prop.get('goal_description',''))
        trajectories.append(dict(id=ident,variant=variant,actions=len(rr),flagged=n))
    gzwrite(RESULTS/'offline_action_audit.jsonl.gz',out)
    flagged=[x for x in out if x['assessment']['decision']=='RECONSIDER'];counts=Counter(z['kind'] for x in flagged for z in x['assessment']['reasons'])
    write(RESULTS/'offline_summary.json',dict(actions=len(out),suffixes=20,independent_parent_episodes=1,flagged_actions=len(flagged),
        no_detected_constraint=len(out)-len(flagged),category_counts=dict(counts),
        repeated_failure_confirmed=sum(x['observed_outcome']['repeated_rejection_witness'] for x in flagged),
        flagged_visibility_loss_confirmed=sum('observed_condition_loss_risk' in [z['kind'] for z in x['assessment']['reasons']] and x['observed_outcome']['visibility_lost'] for x in flagged),
        flagged_visibility_loss_not_observed=sum('observed_condition_loss_risk' in [z['kind'] for z in x['assessment']['reasons']] and not x['observed_outcome']['visibility_lost'] for x in flagged),
        resource_or_facility_harm_requires_validation=sum(x['observed_outcome']['exact_task_harm_unknown'] for x in flagged),
        trajectories=trajectories,new_model_calls=0,not_counterfactual_prevented_errors=True,
        caveat='Shadow flags on unchanged historical actions, not actual prevention. ALLOW means no detected constraint, not proof the action has no effect. Resource custody loss is a risk, not proven task harm.'))
    print(json.dumps(read(RESULTS/'offline_summary.json')),flush=True)

if __name__=='__main__':main()
