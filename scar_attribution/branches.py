"""Frozen-state candidate and intervention branches. No model/provider imports."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import copy
import hashlib
import json
import logging
import multiprocessing as mp
from pathlib import Path
import tempfile
import time

from scar.environment import restore,snapshot,state_digest
from scar.io import atomic_json,digest
from scar_v3.hard import goal_reached
from scar_attribution.search import bounded,execute,key,replay_path


def multistep_choice(audit,branches,k,oracle=False):
    values=audit["C1_values"] if oracle else audit["C0_values"]
    scored=[]
    for i,v in enumerate(values):
        b=branches[v["action"]];d=b["distance"]
        q=.9**(d-1) if d is not None and d<=k else 0.
        p=1-v["probability_of_success"];confidence=v["evidence_confidence"]
        value=(1-p)*1.7*q-.8*p-.35*(1-confidence)-.08*v["extra_call_cost"]-(.15 if i else 0)
        if not v["allowed"]:value=-2.
        scored.append({"action":v["action"],"allowed":v["allowed"],"value":value,"q_verified_lower_bound":q,"confidence":confidence,"learned_or_oracle_failure_probability":p})
    base=scored[0]
    eligible=[s for s in scored[1:] if s["allowed"] and s["value"]-base["value"]>.2 and s["confidence"]>=.65 and s["q_verified_lower_bound"]>0]
    picked=max(eligible,key=lambda s:(s["value"],s["action"])) if eligible else base
    if not picked["allowed"]:
        valid=[s for s in scored[1:] if s["allowed"]]
        picked=max(valid,key=lambda s:s["value"]) if valid else None
    return {"action":picked["action"] if picked else None,"values":scored,"interpretation":"Oracle verified path lower-bound scoring; not a new closed-loop agent"}


def state_job(job):
    state,case,runtime,outdir,budgets=job;tick=time.monotonic();logging.disable(logging.CRITICAL)
    out=Path(outdir)/"branches"/(state["state_id"]+".json")
    if out.exists():return {"state_id":state["state_id"],"cached":True}
    audit_all=json.loads((Path(outdir)/"audits"/(case["id"]+".json")).read_text())
    audit=audit_all["rows"][state["index"]]
    assert audit["record_digest"]==state["record_digest"]
    assert audit["candidate_actions"]==state["candidate_actions"]
    branches={};cache={};limits={k:budgets[k] for k in ["max_expanded","max_generated","max_frontier"]}
    with tempfile.TemporaryDirectory(prefix="scar-attribution-search-") as temp:
        root=restore(audit["state_snapshot"],temp);start=snapshot(root)
        assert state_digest(root)==audit["state_digest"]
        for action in state["candidate_actions"]:
            cached=False
            env=restore(start,temp);done,invalid=execute(env,action);data=snapshot(env)
            if goal_reached(env,case["goal"]):
                tail={"status":"ALREADY_REACHED","path":[],"distance":0,"expanded":0,"generated":0,"seconds":0}
            elif done:
                tail={"status":"TERMINATED","path":None,"distance":None,"expanded":0,"generated":0,"seconds":0}
            else:
                cachekey=hashlib.sha256(data).hexdigest()
                cached=cachekey in cache
                if not cached:cache[cachekey]=bounded(data,case["goal"],max_depth=state["max_depth"]-1,**limits)
                tail=copy.deepcopy(cache[cachekey])
            distance=1+tail["distance"] if tail["distance"] is not None else None
            path=[action]+tail["path"] if tail["path"] is not None else None
            verify=replay_path(start,path,case["goal"]) if path else None
            if verify and not verify["verified"]:raise AssertionError("Whole first-action branch failed exact replay")
            branches[action]={"first_action":action,"distance":distance,"path":path,"verified":bool(verify and verify["verified"]),"terminal_without_goal":done and not goal_reached(env,case["goal"]),"first_engine_invalid":invalid,"search":tail,"search_cache_reused":cached,"verification":verify,"at_k":{str(k):"VERIFIED" if distance is not None and distance<=k else "TERMINATED" if done and distance is None else "UNKNOWN" for k in [5,10,20] if k<=state["max_depth"]}}
        # Independent candidate-generation upper bound. Reference witness is
        # permitted ONLY here at the original initial state, never in C0-C3.
        upper=bounded(start,case["goal"],max_depth=state["max_depth"],**limits)
        upper["source"]="independent_bounded_search"
        if state["index"]==0:
            reference=replay_path(start,case["witness"],case["goal"])
            if not reference["verified"]:raise AssertionError("Initial reference witness failed replay")
            upper["reference_witness_check"]={"distance":len(case["witness"]),"verified":True}
            if upper["distance"] is None or len(case["witness"])<upper["distance"]:
                upper.update(path=case["witness"],distance=len(case["witness"]),verification=reference,status="VERIFIED",source="separately_labelled_frozen_reference_witness")
        upper["first_action_in_original_candidates"]=bool(upper["path"] and upper["path"][0] in branches)
        upper["candidate_augmentation_only"]=True
    selected={}
    for k in [5,10,20]:
        if k<=state["max_depth"]:
            selected[str(k)]={"C0":{"action":audit["C0"]},"C1":{"action":audit["C1"]},"C2":multistep_choice(audit,branches,k),"C3":multistep_choice(audit,branches,k,True)}
    result={"state":state,"initial_state_digest":audit["state_digest"],"branches":branches,"upper":upper,"conditions":selected,"seconds":time.monotonic()-tick,"api_calls":0,"source_audit_digest":digest(audit),"protocol_search":budgets}
    atomic_json(out,result)
    return {"state_id":state["state_id"],"seconds":result["seconds"],"candidates":len(branches),"verified":sum(b["verified"] for b in branches.values())}


def main():
    p=argparse.ArgumentParser();p.add_argument("--runtime",required=True);p.add_argument("--output",required=True);p.add_argument("--workers",type=int,default=8);p.add_argument("--state",default=None)
    args=p.parse_args();root=Path("results/v3/attribution")
    states=json.loads((root/"state_manifest.json").read_text());protocol=json.loads((root/"protocol.json").read_text());freeze=json.loads((root/"protocol_freeze.json").read_text())
    assert digest(states)==freeze["state_list_sha256"] and digest(protocol)==freeze["protocol_sha256"]
    cases={c["id"]:c for c in json.loads(Path("results/v3/dataset/cases.json").read_text())}
    states=[s for s in states if not args.state or s["state_id"]==args.state]
    tick=time.monotonic();completed=0
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=mp.get_context("spawn")) as pool:
        futures=[pool.submit(state_job,(s,cases[s["case_id"]],args.runtime,args.output,protocol["search"])) for s in states]
        for future in as_completed(futures):
            result=future.result();completed+=1;print(json.dumps(result|{"completed":completed,"expected":len(states)}),flush=True)
            atomic_json(Path(args.output)/"search_status.json",{"state":"running" if completed<len(states) else "finished","completed":completed,"expected":len(states),"wall_seconds":time.monotonic()-tick,"updated":time.time(),"api_calls":0})


if __name__=="__main__":main()
