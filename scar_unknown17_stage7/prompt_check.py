"""Post-freeze zero-API full-history C0 request and agent checkpoint audit."""
import contextlib
import copy
import gzip
import json
from pathlib import Path
import tempfile
from scar.io import atomic_json
from scar_sequence.prepare import NoAPIProvider
from scar_unknown17.agent import make_agent as old_agent
from scar_unknown17_stage7.agent import make_agent as new_agent

class RecordedProposal(NoAPIProvider):
    def __init__(self):super().__init__();self.action='wait';self.last=None
    def generate(self,*args,**kwargs):
        self.last=(copy.deepcopy(args),copy.deepcopy(kwargs))
        response={'action':self.action,'reasoning':'zero API, recorded base proposal'}
        return {'response':json.dumps(response),'parsed':response,'num_input_tokens':0,'num_output_tokens':0}


def main():
    cases={c['id']:c for c in json.loads(Path('results/stage7/cases.json').read_text())}
    cfg=json.loads(Path('configs/protocol_stage7.json').read_text());checks=[];roundtrips=[]
    with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for ep in map(json.loads,gzip.open('results/unknown17/trajectories_FIFOCombined.jsonl.gz','rt')):
            case=cases[ep['case_id']];pa,pb=RecordedProposal(),RecordedProposal()
            aa=old_agent('FIFOCombined',case['game'],pa,cfg,Path(tmp)/'a');bb=new_agent('C0',case['game'],pb,cfg,Path(tmp)/'b')
            for ag in [aa,bb]:
                ag.cfg.system_prompt+='\nExperiment recovery objective (priority for this episode): '+case['public_goal']
                for h in case['history']:
                    ag.memorize(f"{h['before']['text']}\nAction: {h['action']}\n{h['after']['text']}")
                    ag.observe_transition(h['before'],h['action'],h['after'])
                ag.memorize('Recovery objective: '+case['public_goal']);ag.set_recovery_objective(case['target_action'],case['public_goal'])
                ag.events.clear()
            for r in ep['rows']:
                pa.action=pb.action=r['proposed_action'];a1=aa.act(r['observation'])[0];a2=bb.act(r['observation'])[0]
                checks.append({'case_id':case['id'],'index':r['index'],'same_request':pa.last==pb.last,
                    'same_action':a1==a2==r['executed_action'],'same_memory':aa.short_term_memory==bb.short_term_memory,
                    'same_fact_summary':aa.decision['fact_summary']==bb.decision['fact_summary']})
                for ag in [aa,bb]:ag.observe_transition(r['observation'],r['executed_action'],r['next_observation']);ag.events.clear()
            directory=Path(tmp)/'reload';directory.mkdir(exist_ok=True);bb.save_memory(directory)
            restored=new_agent('C0',case['game'],RecordedProposal(),cfg,Path(tmp)/'c');restored.load_memory(directory)
            roundtrips.append({'case_id':case['id'],'controller':restored.controller.to_dict()==bb.controller.to_dict(),
                'facts':restored.facts.to_dict()==bb.facts.to_dict(),'memory':restored.short_term_memory==bb.short_term_memory})
    passed=all(all(x[k] for k in ['same_request','same_action','same_memory','same_fact_summary']) for x in checks) and all(all(x[k] for k in ['controller','facts','memory']) for x in roundtrips)
    result={'api_calls':0,'actions':len(checks),'families':17,'after_freeze':True,'policy_changes':False,'passed':passed,'checks':checks,'full_agent_roundtrips':roundtrips}
    atomic_json('results/stage7/full_prompt_parity.json',result);print(json.dumps({k:v for k,v in result.items() if k not in {'checks','full_agent_roundtrips'}}));assert passed

if __name__=='__main__':main()
