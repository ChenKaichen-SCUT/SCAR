"""Freeze all candidate interpretations before evaluating their outcomes."""
import datetime
from pathlib import Path
from scar.io import atomic_json,digest
from scar_stage12.public import primitive_candidate
from scar_stage14.common import ROOT,OLD,load,sha,records
from scar_stage14.intents import normalize,recorded_goal
from scar_stage14.intent_annotations import GOALS,DESTINATIONS,AMBIGUOUS


def main():
    assert not (ROOT/'executor_freeze.json').exists()
    states=load(OLD/'states.json');js=load(OLD/'judgments.json')
    old={r['state_id']:r for r in records(OLD/'native_branches.jsonl.gz')}
    intents={};refs=[];annotations=[];publics={}
    def add(s,c,role,goal=None,**extra):
        pub=publics[s['state_id']];i=normalize(pub,c,goal);key=(s['state_id'],i['id'])
        if key in intents:
            for e in i['evidence']:
                if e not in intents[key]['intent']['evidence']:intents[key]['intent']['evidence'].append(e)
        else:intents[key]={'state_id':s['state_id'],'intent':i}
        refs.append({'state_id':s['state_id'],'candidate_id':c['id'],'intent_id':i['id'],'role':role,**extra})
    for s in states:
        publics[s['state_id']]={'controller':s['public_controller'],'observation':s['observation'],'remaining_actions':s['remaining_actions']}
        # Candidate metadata only; no native score is read when normalizing.
        for b in old[s['state_id']]['branches'].values():add(s,b['candidate'],'pool')
        for m in ['J0','J1']:
            a=s['rule_actions'][m];add(s,primitive_candidate(a),m,recorded_goal(s['rule_decisions'][m],a),replicate=0)
        for j in [j for j in js if j['state_id']==s['state_id']]:
            if j.get('validation_errors') or not j.get('parsed'):continue
            if j['method']=='J3':
                ids=[j['parsed']['selected_candidate_id']]+j['parsed'].get('ranked_candidate_ids',[])
                menu={c['id']:c for c in s['candidates']}
                for rank,cid in enumerate(dict.fromkeys(ids)):
                    if cid in menu:add(s,menu[cid],'J3' if rank==0 else 'J3_rank',replicate=j['replicate'],rank=rank)
            else:
                key=(s['state_id'],j['replicate']);reason=j['parsed']['reasoning'];goal=None
                if key in GOALS:
                    assert GOALS[key] in reason
                    goal={'target':GOALS[key],'operation':'craft_inspect','evidence':{'saved_J2_reasoning':reason,'reasoning_digest':digest(reason),'annotation':'explicit next production target; inspect is common evaluation closure'}}
                elif key in DESTINATIONS:
                    goal={'target':DESTINATIONS[key],'location':DESTINATIONS[key],'operation':'move','evidence':{'saved_J2_reasoning':reason}}
                annotations.append({'state_id':key[0],'replicate':key[1],'action':j['parsed']['action'],'reasoning':reason,
                    'goal':goal,'incomplete_reason':AMBIGUOUS.get(key),'source':'Stage12 saved response, no new model call'})
                add(s,primitive_candidate(j['parsed']['action']),'J2',goal,replicate=j['replicate'])
    atomic_json(ROOT/'intent_public_inputs.json',publics)
    atomic_json(ROOT/'candidate_intents.json',list(intents.values()))
    atomic_json(ROOT/'intent_references.json',refs);atomic_json(ROOT/'J2_intent_annotations.json',annotations)
    protocol={
        'scope':'all original 363 candidates plus method-specific explicit intentions at the same 50 checkpoints',
        'windows':[4,6,8],'max_remaining_original_budget':40,'api_calls':0,
        'first_action':'exact candidate action; illegal first actions are never repaired retrospectively',
        'normalization':'explicit candidate metadata or each method own saved goal; J2 reasoning manually annotated; no rival goal borrowing',
        'atomic_incomplete':'stop after declared acquisition/move if no unique downstream intention; report separately',
        'neutral_craft_closure':'after actual production, inspect that product; this convention is not proof that historical agent committed to inspect',
        'executor':'historical K2 only; same acquisition/batch primitives, known station routes; no new exploration ranking or recursive synthesis',
        'knowledge_updates':'record every disclosure, keep the same declared target; no outcome-directed retargeting',
        'factorial_panels':{'original':'old executor + K2 scoring','parser_only':'old executor + K1 scoring',
            'executor_only':'unified executor + K2 scoring','both':'unified executor + K1 scoring'},
        'factorial_limitation':'K1 changes measurement only, not planning inputs; no calibrated online-agent performance is estimated',
        'cache':'select public action first; reuse only matching full action prefixes from deterministic native traces; otherwise native replay',
        'continuity_gate':['explicit recorded exploratory goal','actual acceptance/start','supported next public step',
            'unfinished in full actual remaining trajectory','same-input neutral native continuation completes','no important new information/resources/risk/goal reason for switch'],
        'statistics':'paired within state; report family aggregates, no iid inference over 50 states',
        'prior_outcomes_known':True,'new_native_outcomes_used_to_tune':False,
        'decision':'NO-GO for new mechanism absent replicated strict continuity failures beyond fixed continuation; otherwise INCONCLUSIVE unless decisive evidence'}
    atomic_json(ROOT/'intent_protocol.json',protocol)
    paths=[Path('scar_stage14')/p for p in ['intents.py','executor.py','intent_annotations.py','prepare_intents.py','test_executor.py']]
    paths += [ROOT/p for p in ['intent_public_inputs.json','candidate_intents.json','intent_references.json','J2_intent_annotations.json','intent_protocol.json']]
    atomic_json(ROOT/'executor_freeze.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'hashes':{str(p):sha(p) for p in paths},'api_calls':0,'frozen_before_new_native_results':True})
    print({'states':len(publics),'unique_intents':len(intents),'references':len(refs)})

if __name__=='__main__':main()
