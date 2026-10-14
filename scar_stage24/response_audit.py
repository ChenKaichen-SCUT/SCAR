"""Audit model output JSON and required fields independently of transport."""
from .common import *
from .analyze import final_folder


def main():
    offline();out=[]
    for game in GAMES:
        folder=final_folder(game);rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz')
        decisions={r['step']:r['decision'] for r in rr}
        if (folder/'decision_exhausted.json').exists():
            d=read(folder/'decision_exhausted.json');decisions[d['step']]=d['decision']
        for q in qq:
            raw=q['raw_response']['choices'][0];problems=[];parsed=None
            try:parsed=json.loads(raw['message']['content'])
            except (ValueError,TypeError):problems.append('invalid_json')
            if isinstance(parsed,dict):
                for name in ['reasoning','action','goal_description','goal_evidence']:
                    if not isinstance(parsed.get(name),str):problems.append('missing_or_nonstring_'+name)
            elif parsed is not None:problems.append('json_not_object')
            if raw['finish_reason']!='stop':problems.append('finish_reason:'+raw['finish_reason'])
            if not problems:continue
            d=decisions[q['step']]
            out.append(dict(game=game,step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],issues=problems,
                usage=q['usage'],finish_reason=raw['finish_reason'],controller_reasons=d['attempts'][q['ordinal']-1]['reasons'],
                executed_action=d['executed_action'],subsequent_model_calls_within_decision=len(d['attempts'])-q['ordinal'],
                raw_response_reference=str(folder.relative_to(ROOT)/'requests.jsonl.gz')+f"#request_id={q['request_id']}"))
    write(RESULTS/'response_anomalies.json',out);print(json.dumps(dict(affected_responses=len(out),cases=[(r['game'],r['step']) for r in out])))

if __name__=='__main__':main()
