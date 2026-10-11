"""Zero-API audit of every V3 hard decision and its frozen candidate set."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import copy
import json
import logging
import multiprocessing as mp
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace

from scar.environment import restore,snapshot,state_digest,AGENT_ID
from scar.io import atomic_json,digest
from scar_v3.learning import PreconditionLearner
from scar_v3.state import PublicState
from scar_v3.selection import Selector
from scar_v3.hard import goal_reached
from scar_attribution.oracle import OraclePreconditions,conditions,progress
from scar_attribution.search import execute,physical_key


def initial_memory(case):
    from scar_v3.agent import SCARV3Agent
    agent=SimpleNamespace(learner=PreconditionLearner(),selector=Selector(),public_state=None,pending_transition=None,goal_action="",public_objective=None,plan={"actions":[],"goal":"","created":0,"location":None},events=[],last_intervention=None)
    for r in case["history"]:
        SCARV3Agent.observe_transition(agent,r["before"],r["action"],r["after"])
    return {"learner":agent.learner.to_dict(),"selector_outcomes":agent.selector.outcomes,"public_state":agent.public_state.to_dict() if agent.public_state else None,"plan":agent.plan,"goal_action":case["target_action"]}


def pre_action_memory(case,paths,index,row):
    # Saved checkpoints follow observe_transition: using the current checkpoint
    # would leak this action's outcome. Use the previous one, or replay only the
    # shared initial history, then exactly reproduce _act's public-state refresh.
    memory=initial_memory(case) if index==0 else json.loads((paths[index-1].parent/"memory/scar_v3.json").read_text())
    previous=PublicState.from_dict(memory["public_state"]) if memory["public_state"] else None
    memory["public_state"]=PublicState.observe(row["observation"],previous).to_dict()
    return memory


def choose(selector,base,candidates):
    picked,reason=selector.choose(base,candidates)
    if not picked.allowed:
        valid=[v for v in candidates if v.allowed]
        if not valid:return None,"method_termination"
        picked=max(valid,key=lambda v:v.value);reason="mandatory_format_correction"
    return picked,reason


def values(row,memory,learner=None):
    learner=learner or PreconditionLearner.from_dict(memory["learner"])
    state=PublicState.from_dict(memory["public_state"])
    selector=Selector();selector.outcomes=copy.deepcopy(memory["selector_outcomes"])
    base=selector.score(row["proposed_action"],row["goal_action"],state,learner,row["base_value"]["allowed"])
    candidates=[selector.score(v["action"],row["goal_action"],state,learner,v["allowed"],extra_call_cost=v["extra_call_cost"],switching=True) for v in row["candidate_values"]]
    picked,reason=choose(selector,base,candidates)
    return base,candidates,picked,reason


def family_job(job):
    case,runtime,output=job;tick=time.monotonic();logging.disable(logging.CRITICAL)
    run=next(Path(runtime).glob(f"runs/hard-{case['id']}-SCARV3Agent-*"))
    summary=json.loads((run/"summary.json").read_text());out=Path(output)/"audits"/(case["id"]+".json")
    if out.exists():return {"case":case["id"],"cached":True}
    paths=sorted(run.glob("steps/*/transition.json"));audits=[];seen=Counter();badconditions=[]
    with tempfile.TemporaryDirectory(prefix="scar-attribution-audit-") as temp:
        for index,path in enumerate(paths):
            row=json.loads(path.read_text());memory=pre_action_memory(case,paths,index,row)
            initial=run/"initial.pkl" if index==0 else paths[index-1].with_name("environment.pkl")
            env=restore(initial,temp);saved=snapshot(env)
            base,candidates,picked,reason=values(row,memory)
            assert picked and picked.action==row["executed_action"],(case["id"],index,"C0 action mismatch")
            for a,b in zip([base]+candidates,[row["base_value"]]+row["candidate_values"]):
                assert abs(a.value-b["value"])<1e-10,(case["id"],index,"C0 score mismatch")
            oracle=OraclePreconditions(env)
            ob,oc,op,oreason=values(row,memory,oracle)
            original_goal=conditions(env,case["target_action"])
            actions=list(dict.fromkeys(row["all_proposals"]))
            outcomes={}
            for action in actions:
                truth=oracle.cache.get(action) or conditions(env,action)
                if truth["condition_dispatch_match"] is False:badconditions.append([index,action,truth])
                child=restore(saved,temp);done,invalid=execute(child,action)
                after=conditions(child,case["target_action"])
                outcomes[action]={"truth":truth,"goal_conditions_after":after,"progress":progress(original_goal,after),"physical_goal":goal_reached(child,case["goal"]),"physical_noop":physical_key(env)==physical_key(child),"child_physical_key":physical_key(child),"child_state_digest":state_digest(child),"done":done,"engine_invalid":invalid}
                if action==row["executed_action"]:
                    assert state_digest(child)==state_digest(restore(path.with_name("environment.pkl"))), (case["id"],index,"actual replay differs")
            target_prediction=PreconditionLearner.from_dict(memory["learner"]).predict(case["target_action"],PublicState.from_dict(memory["public_state"])).to_dict()
            visible_facts=PreconditionLearner.from_dict(memory["learner"]).features(case["target_action"],PublicState.from_dict(memory["public_state"]))
            visibility={k:visible_facts[k].to_dict() if k in visible_facts else {"truth":"UNREPRESENTED"} for k in original_goal["facts"]}
            pk=physical_key(env);seen[pk]+=1
            audits.append({"index":index,"state_digest":state_digest(env),"physical_key":pk,"revisit_count":seen[pk]-1,"state_snapshot":str(initial),"record_digest":digest(row),"goal_action":row["goal_action"],"target_action":case["target_action"],"goal_conditions":original_goal,"public_target_facts":visibility,"learned_target_prediction":target_prediction,"learned_base_prediction":base.prediction,"C0":picked.action,"C1":op.action if op else None,"C1_reason":oreason,"C0_values":[base.to_dict()]+[x.to_dict() for x in candidates],"C1_values":[ob.to_dict()]+[x.to_dict() for x in oc],"candidate_actions":actions,"outcomes":outcomes,"intercepted":row["intercepted"],"proposed_action":row["proposed_action"],"executed_action":row["executed_action"],"memory_plan":memory["plan"],"events":row["events"],"rule_count":len(memory["learner"]["feedback_rules"]),"hypothesis_count":sum(len(v.get("hypotheses",[])) for v in memory["learner"]["models"].values())})
    record={"case_id":case["id"],"family":case["family"],"summary":{k:summary[k] for k in ["task_id","status","steps","recovery_at_40","error"]},"rows":audits,"condition_mismatches":badconditions,"seconds":time.monotonic()-tick}
    atomic_json(out,record)
    if badconditions:raise AssertionError(f"Oracle condition mismatch {case['id']}; inspect saved evidence")
    return {"case":case["id"],"rows":len(audits),"seconds":record["seconds"]}


def main():
    p=argparse.ArgumentParser();p.add_argument("--runtime",required=True);p.add_argument("--output",required=True);p.add_argument("--workers",type=int,default=8);p.add_argument("--case",default=None)
    args=p.parse_args();cases=[c for c in json.loads(Path("results/v3/dataset/cases.json").read_text()) if c["split"]=="test" and (not args.case or c["id"]==args.case)]
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=mp.get_context("spawn")) as pool:
        for result in pool.map(family_job,[(c,args.runtime,args.output) for c in cases]):print(json.dumps(result),flush=True)


if __name__=="__main__":main()
