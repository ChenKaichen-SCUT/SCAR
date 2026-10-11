"""Freeze the exploratory attribution protocol and state list before oracle scoring."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

from scar.io import atomic_json, digest


def load_traces(formal, method):
    groups = defaultdict(list)
    with gzip.open(Path(formal)/f"trajectories_{method}.jsonl.gz", "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["task"]["stage"] == "hard":
                groups[r["task"]["family"]].append(r["transition"])
    return groups


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="results/v3/attribution")
    args = p.parse_args()
    out = Path(args.output)
    if (out/"protocol.json").exists():
        raise SystemExit("Protocol already frozen; refusing overwrite")
    cases = [c for c in json.loads(Path("results/v3/dataset/cases.json").read_text()) if c["split"] == "test"]
    summaries = [s for s in json.loads(Path("results/v3/formal/all_summaries.json").read_text()) if s["stage"] == "hard"]
    runs = defaultdict(dict)
    for s in summaries:
        runs[s["family"]][s["algorithm"]] = s
    pairs = []
    for c in sorted(cases, key=lambda c:c["family"]):
        scores = {m:s["recovery_at_40"] for m,s in runs[c["family"]].items()}
        group = ("both_success" if scores["ShortTermMemoryAgent"] else "v3_only") if scores["SCARV3Agent"] else ("stm_only" if scores["ShortTermMemoryAgent"] else "both_failure")
        pairs.append({k:c[k] for k in ["id","family","game","source_cluster","mechanism_cluster","types","target_action","public_goal"]} | {"group":group,"recovery_at_40":scores,"tasks":{m:s["task_id"] for m,s in runs[c["family"]].items()}})
    assert Counter(x["group"] for x in pairs) == {"v3_only":4,"stm_only":12,"both_success":44,"both_failure":29}
    detailed = {x["family"] for x in pairs if x["group"] in {"v3_only","stm_only"}}
    for group in ["both_success","both_failure"]:
        detailed.update(x["family"] for x in sorted((x for x in pairs if x["group"]==group),key=lambda x:digest(["attribution-control-20261012",x["family"]]))[:4])
    traces = load_traces("results/v3/formal", "SCARV3Agent")
    states=[]
    for c in sorted(cases,key=lambda c:c["family"]):
        rows=traces[c["family"]]
        selected=defaultdict(list)
        selected[0].append("all_family_initial_decision")
        for r in rows:
            if r["intercepted"]:
                selected[r["index"]].append("all_hard_interventions")
        if c["family"] in detailed:
            for i in sorted({0,len(rows)//4,len(rows)//2,3*len(rows)//4,len(rows)-1}):
                selected[i].append("detailed_predeclared_quartiles")
        for i,reasons in sorted(selected.items()):
            r=rows[i]
            states.append({"state_id":f"{c['id']}--{i:03d}","case_id":c["id"],"family":c["family"],"task_id":runs[c["family"]]["SCARV3Agent"]["task_id"],"index":i,"reasons":reasons,"long_chain":"long_recovery_chain" in c["types"],"candidate_actions":r["all_proposals"],"record_digest":digest(r),"max_depth":20 if "long_recovery_chain" in c["types"] else 10})
    protocol={
        "frozen_at_utc":datetime.now(timezone.utc).isoformat(),"source_commit":"61a23ff4bfb6e9b0c81a7fc78eb3d6bc9c54c957",
        "scope":"Exploratory mechanism diagnosis on already-seen tests; no new deployable agent or generalization claim.",
        "new_api_calls":0,"paid_authorization":"User authorized this new round without a monetary cap; no paid calls planned or necessary for offline protocol.",
        "families":89,"paired_groups":dict(Counter(x["group"] for x in pairs)),"detailed_families":sorted(detailed),
        "state_sampling":"All 89 initial V3 decisions, all 141 interventions, and decision quartiles of 16 discordant + hash-selected 4 both-success + 4 both-failure families; deduplicate by family/index.",
        "states":len(states),"state_list_digest":digest(states),
        "single_step_scope":"Every committed V3 hard action and every logged candidate; reconstruct saved pre-action learner and selector; check original C0 scoring exactly.",
        "search":{"algorithm":"Deterministic bounded weighted best-first search on full official-engine transitions; priority g+2*h; admissibility/minimality NOT claimed.","max_expanded":256,"max_generated":4096,"max_frontier":1024,"depths":[5,10],"long_chain_max_depth":20,"workers":8,"gamma":0.9,"vocabulary":"Recursive goal recipe ingredients/products, relevant item/container transfers, all neighboring movement, key and torch. No reference witness or future logged actions are supplied to C0-C3 searches.","state_abstraction":"Physical inventory/map + task/quest/combat state and clock; full paths replayed twice. Search failure, frontier pruning and node/depth limits are UNKNOWN, never proof of impossibility.","budget_policy":"Same fixed bounds for each distinct first action; exact-state cache only, no result-driven reruns or tuning."},
        "conditions":{
            "C0":"Frozen learner, saved public state/outcome history, original Selector.score/choose; reproduce recorded action.",
            "C1":"Replace predict with true action-rule rejection (p=0/1, confidence=1) and actual violated conditions. Original public state, goal, candidate multiset, costs, score/choose unchanged. No route/next-action data.",
            "C2":"Retain learned p/confidence and extra-call/switch costs. Replace single-step task term with 1.7*Q_K, Q_K=0.9**(d-1) for a replay-verified path of length d<=K, else zero verified lower bound. Retain margin .2 and confidence>=.65; switch only to candidate with verified positive Q_K. This is a conservative diagnostic of the value term; separately report ungated candidate upper bound.",
            "C3":"Same as C2, with Oracle precondition p/confidence. Candidate list/state/goal/search outputs identical to C2.",
            "bounds":"Q_K=0 means no verified witness found, NOT true zero value. All improvements are witness-discovery/lower-bound changes; report unknown and paired identification bounds. Distances are shortest FOUND verified paths, never global shortest.",
            "upper":"Independent search from the frozen state with broader diagnostic vocabulary; its first action may be added ONLY in a separately-labelled candidate-generation upper bound. Frozen dataset witness may be replayed ONLY at initial states in this separate upper bound. Never feed it to C0-C3."
        },
        "intervention_metrics":{"MSIB":"Paired verified-path discovery difference at K for recorded intervention vs base first action, plus interval accounting for UNKNOWN on either branch; not closed-loop agent Recovery@K.","waste":"Report proven physical no-op/cycles separately; no condition progress and no found path is only unverified progress, not definitive waste. Strict zero-task-progress only when a branch immediately ends without goal; all censored cases remain unknown."},
        "statistics":"One family is a cluster. Family-mean paired differences, fixed 10000 bootstrap seed 20261012; source/mechanism sensitivity; descriptive exploratory comparisons without multiplicity claims.",
        "protected_inputs":{"cases":"results/v3/dataset/cases.json","formal":"results/v3/formal/","implementation":"scar_v3/"},
        "data_digest":digest(json.loads(Path("results/v3/dataset/cases.json").read_text()))
    }
    atomic_json(out/"pairs.json",pairs)
    atomic_json(out/"state_manifest.json",states)
    atomic_json(out/"protocol.json",protocol)
    atomic_json(out/"protocol_freeze.json",{"protocol_sha256":digest(protocol),"state_list_sha256":digest(states),"pairs_sha256":digest(pairs)})
    print(json.dumps({"pairs":protocol["paired_groups"],"states":len(states),"detailed_families":len(detailed),"api_calls":0}))


if __name__=="__main__":main()
