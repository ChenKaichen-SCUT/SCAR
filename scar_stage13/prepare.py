"""Extract public prefixes, freeze rule definitions/choices before scoring."""
import copy
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from scar.io import atomic_json, digest
from scar_stage12.public import controller, confirmed, primitive_candidate
from scar_stage13.policy import decide
from scar_v3.state import parse_action

OUT = Path('results/stage13')
OLD = Path('results/stage12/diagnostic')
BASE = '9a3bac2f49e4b8bd786ba61b2cefe9d005c5fb7b'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())

def public_history(ep, stop):
    history = []
    for r in ep['rows']:
        if r['index'] >= stop: break
        c = controller(r['stage7_state_before'], r['observation']); t = c.table
        old = {n for n, x in t.recipes.items() if x.get('ingredients')}
        nodes = confirmed(c); p = parse_action(r['executed_action'])
        unconnected = (p.verb == 'inspect' and p.target not in nodes and p.target not in t.inspected
            and p.target not in t.containers and p.target not in c.quantity_facts.produced
            and not t.recipes.get(p.target, {}).get('ingredients')
            and p.target not in {n for x in t.recipes.values() for n in x.get('stations', [])})
        new_place = p.verb == 'enter' and p.target not in t.places
        old_location = t.state.get('location')
        previous_count = c.ownership(p.target)['lower_bound']
        c.observe(r['observation'], r['executed_action'], r['next_observation'])
        now = {n for n, x in t.recipes.items() if x.get('ingredients')}
        feedback = t.state['feedback']; new = now-old
        blocked = c.attempt_log[-1].get('state') != 'SUCCESS' if c.attempt_log else False
        # Progress uses only witnessed public effects. Repeated known-room moves
        # do not reset it; acquisition and crafting do, including preparatory
        # products whose eventual goal connection remains unknown.
        acquired = c.ownership(p.target)['lower_bound'] > previous_count
        made = p.verb == 'craft' and 'successfully crafted' in feedback
        moved_new = new_place and t.state.get('location') != old_location
        necessary = new & confirmed(c)
        history.append({'index': r['index'], 'action': r['executed_action'],
            'before': r['observation'], 'after': r['next_observation'], 'feedback': feedback,
            'new_recipes': sorted(new), 'new_public_necessary_recipes': sorted(necessary),
            'public_acquisition': acquired, 'public_production': made, 'new_place': moved_new,
            'progress': bool(new or acquired or made or moved_new), 'blocked': blocked,
            'unconnected_inspection': unconnected})
    assert len(history) == stop
    return history


def main():
    assert not (OUT/'freeze.json').exists(), 'Do not overwrite the frozen strategy.'
    assert subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip() == BASE
    prior = {p: sha(p) for p in subprocess.check_output(['git','ls-files','-z']).decode().split('\0') if p}
    atomic_json(OUT/'prior_manifest.json', prior)
    states = load(OLD/'states.json'); judgments = {(j['state_id'],j['method'],j['replicate']):j for j in load(OLD/'judgments.json')}
    episodes = {}; sources = []
    for stage, methods in [(10,['S1']), (11,['E0','E1'])]:
        for method in methods:
            path = Path(f'results/stage{stage}/trajectories_{method}.jsonl.gz'); sources.append(str(path))
            for ep in map(json.loads, gzip.open(path,'rt')): episodes[ep['task_id']] = ep
    inputs = []; decisions = []; audit = []
    for s in states:
        ep = episodes[s['source_task']]; row = ep['rows'][s['source_index']]
        assert row['observation'] == s['observation'] and row['proposed_action'] == s['frozen_base_proposal']
        assert row['executed_action'] == s['rule_actions']['J0'] and row['stage7_state_before'] == s['public_controller']
        public = {'controller': copy.deepcopy(s['public_controller']), 'observation': s['observation'],
            'candidates': s['candidates'], 'history': public_history(ep,s['source_index']),
            'base_proposal': s['frozen_base_proposal'], 's1_action': s['rule_actions']['J0'],
            'remaining_actions': s['remaining_actions'],
            'j3_selected': judgments[(s['state_id'],'J3',0)]['parsed']['selected_candidate_id']}
        inputs.append({'state_id': s['state_id'], 'public': public})
        decisions.append({'state_id':s['state_id'], **decide(public)})
        audit.append({'state_id':s['state_id'], 'source_task':s['source_task'], 'prefix_rows':len(public['history']),
            'exclusive_stop_index':s['source_index'], 'source_row_exact':True, 'public_input_digest':digest(public)})
    atomic_json(OUT/'public_inputs.json', inputs); atomic_json(OUT/'decisions.json', decisions)
    atomic_json(OUT/'source_audit.json', audit)
    # Diagnostic supplements cannot affect frozen choices. All base proposals,
    # and all original action-limit branches (not selected positive cases).
    old = {r['state_id']:r for r in map(json.loads,gzip.open(OLD/'native_branches.jsonl.gz','rt'))}
    jobs = []; reuse = []
    for s in states:
        c = primitive_candidate(s['frozen_base_proposal']); bs = old[s['state_id']]['branches']
        if c['id'] in bs: reuse.append({'state_id':s['state_id'], 'candidate_id':c['id'], 'kind':'base_proposal'})
        else: jobs.append({'state_id':s['state_id'], 'candidate':c, 'limit':4, 'kind':'base_proposal'})
        for b in bs.values():
            if b['stop'] == 'action_limit' and s['remaining_actions'] > 4:
                jobs.append({'state_id':s['state_id'], 'candidate':b['candidate'], 'limit':8, 'kind':'truncation_sensitivity'})
    atomic_json(OUT/'supplement_plan.json', {'jobs':jobs, 'reused_base_proposals':reuse,
        'selection':'all 50 frozen base proposals; every Stage12 branch stopped at action_limit; no outcome filtering',
        'main_limit':4, 'sensitivity_limit':8, 'report_prefix6_separately':True})
    protocol = {'base_commit':BASE, 'scope':'same developed 50 states / original10 robot_kingdom families',
        'no_new_api':True, 'no_new_closed_loop':True, 'independent_validation':False,
        'thresholds':{'drought_actions':3,'coverage_cooldown_actions':4,'reserve_actions':2,'main_limit':4,'sensitivity_limit':8},
        'C0':'exact frozen S1 selected action/common Stage12 executor',
        'C1':'incomplete public dependencies +3 actions in same connected known ingredient component +3 actions without newly publicly connected recipe; 4-action coverage cooldown; least-attempted uninspected unconnected entry, cost then frozen menu tie-break',
        'C2':'incomplete dependencies +3 actions without public recipe/acquisition/production/new-room progress; cooldown; uninspected entry/fresh product/disclosed craft direction; same ordering',
        'C3':'C1 else C2, retaining S1 public base_progress, fresh necessary/product inspection and feasible direct goal craft/collection',
        'L':'C2 trigger, J3 unattempted uninspected public-recipe-supported direction with bounded estimated cost; C3 execution protection',
        'public_unknown':'uninspected unresolved dependency or undisclosed final recipe; inspected raw leaves are not assumed to have hidden recipes',
        'public_cost':'estimate only; known path plus inspect or craft/inspect plus missing input acquisition and known station route; native cap4 remains binding',
        'truth_firewall':'policy accepts whitelist public dict; native recipe_graph only evaluator; features never include native branch cost or labels',
        'dedup':'inspect/visit target share inspect intent; craft batch aliases share craft_then_inspect target; keep first ranked representative and report outcome disagreement; never oracle substitute aliases or backfill Top3',
        'selection_gate':{'minimum_net_gain':2,'minimum_positive_families':2,'maximum_lost_original':1,
            'maximum_added_environment_loss_states':1,'maximum_added_unrelated_consumption_states':0,
            'maximum_harmful_goal_overrides':0},
        'gate_interpretation':'exploratory next-round candidate only; fixed before scoring; otherwise NO-GO, no threshold tuning',
        'attribution':'overlapping diagnostic evidence tags, not independent causal fractions; hypotheses separated',
        'frozen_before_scoring':True, 'previous_stage12_outcomes_already_known':True}
    atomic_json(OUT/'protocol.json',protocol)
    paths = sorted(Path('scar_stage13').glob('*.py')) + [OUT/p for p in ['protocol.json','public_inputs.json','decisions.json','source_audit.json','supplement_plan.json']]
    atomic_json(OUT/'freeze.json', {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'base_commit':BASE, 'prior_file_count':len(prior), 'prior_manifest_sha256':sha(OUT/'prior_manifest.json'),
        'frozen_hashes':{str(p):sha(p) for p in paths}, 'history_sources':{p:sha(p) for p in sources},
        'policy_changes_after_freeze':False, 'api_calls':0, 'decisions':50})
    print(json.dumps({'frozen':True,'states':50,'new_native_jobs':len(jobs),'base_reused':len(reuse),'prior_files':len(prior)}))

if __name__ == '__main__': main()
