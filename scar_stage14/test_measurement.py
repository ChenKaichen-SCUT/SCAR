from scar_stage14.common import ROOT,load,records
from scar_stage14.analyze_intents import annotate,score


def test_native_inventory_success_is_completed_not_physical_failure():
    ks={r['state_id']:r for r in load(ROOT/'frozen_state_knowledge.json')}
    intents={(r['state_id'],r['intent']['id']):r['intent'] for r in load(ROOT/'candidate_intents.json')}
    pubs=load(ROOT/'intent_public_inputs.json');count=0
    for r in records(ROOT/'reused_intent_branches.jsonl.gz'):
        b=r['branch'];i=intents[r['state_id'],r['intent_id']]
        if i['operation']=='inspect' and i['target']=='inventory':
            s=score(b,annotate(ks[r['state_id']],b),4,True,40,i,pubs[r['state_id']],set())
            assert s['intent_complete'] and s['completion_step']==1 and s['actions']==1
            assert b['actions']==1 # frozen execution is unchanged
            count+=1
    assert count==6
