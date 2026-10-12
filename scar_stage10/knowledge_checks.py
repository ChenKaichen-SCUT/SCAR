"""Post-hoc native knowledge bridges, never policy updates or scored successes.

For each failed S2/S3 episode choose the earliest publicly known, native-ready
intermediate whose inspection can disclose a terminal-missing key recipe. This
selection uses evaluator catalogue knowledge and is explicitly non-autonomous.
Compare two actual actions with craft+inspect at the same saved state, twice.
"""
import argparse
import contextlib
import gzip
import hashlib
import json
from pathlib import Path

from scar.io import atomic_json
from scar_sequence.public import ResourceTable
from scar_unknown17.audit import branch
from scar_v3.state import parse_action

OUT = Path('results/stage10')


def main(runtime):
    root = Path(runtime); cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    catalogs = json.loads((OUT/'truth_catalog_evaluation_only.json').read_text())
    records, no_candidate = [], []
    with (root/'knowledge_checks.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for method in ['S2', 'S3']:
            for ep in map(json.loads, gzip.open(OUT/f'trajectories_{method}.jsonl.gz', 'rt')):
                case = cases[ep['case_id']]; assert case['game'] == 'robot_kingdom' and case['cohort'] == 'development_old10'
                if ep['summary']['recovery_at_40']: continue
                missing = ep['summary']['missing_key_recipes']; candidate = None
                for opportunity in ep['summary']['missed_ready_records']:
                    index = opportunity['index']
                    if index+2 > len(ep['rows']): continue
                    for product in sorted(opportunity['nodes']):
                        discoverable = [m for m in missing if product in catalogs[case['id']].get(m, {}).get('ingredients', [])]
                        if discoverable:
                            candidate = (index, product, discoverable); break
                    if candidate: break
                if not candidate:
                    no_candidate.append({'task_id': ep['task_id'], 'missing_key_recipes': missing,
                        'reason': 'no two-step bridge met the stated public-readiness and terminal-missing-recipe filter'})
                    continue
                index, product, discoverable = candidate
                folder = root/'runs'/ep['task_id']
                raw = (folder/'initial.pkl' if index == 0 else folder/'steps'/f'{index:04}'/'environment.pkl').read_bytes()
                actual = [r['executed_action'] for r in ep['rows'][index:index+2]]
                alternatives = ['craft 1 '+product, 'inspect '+product]
                assert index+len(alternatives) <= 40
                native = {'actual_two_actions': branch(raw, actual, case), 'known_production_then_inspect': branch(raw, alternatives, case)}
                base_table = ResourceTable(**ep['rows'][index]['structured']['resource_table'])
                prior = {n for n, r in base_table.recipes.items() if r.get('ingredients')}
                for result in native.values():
                    table = ResourceTable(**ep['rows'][index]['structured']['resource_table'])
                    for tr in result['trace']: table.observe(tr['before']); table.observe(tr['after'], tr['action'])
                    now = {n for n, r in table.recipes.items() if r.get('ingredients')}
                    result['new_recipe_names'] = sorted(now-prior)
                    result['terminal_missing_recipes_revealed'] = sorted((now-prior)&set(missing))
                path = OUT/'knowledge_states'/f'{ep["task_id"]}-{index}.pkl.gz'; path.parent.mkdir(exist_ok=True)
                with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as f: f.write(raw)
                records.append({'task_id': ep['task_id'], 'case_id': case['id'], 'method': method, 'index': index,
                    'publicly_known_product': product, 'missing_recipes_selected_by_evaluator': discoverable,
                    'public_observation': ep['rows'][index]['observation'], 'public_recipe': base_table.recipes.get(product),
                    'state': {'path': str(path), 'serialized_sha256': hashlib.sha256(raw).hexdigest()},
                    'branches': native, 'scope': 'post-hoc evaluator-selected two-action diagnostic; NOT policy-selected or task-completion evidence'})
    result = {'records': records, 'no_candidate': no_candidate, 'api_calls': 0, 'policy_changed': False,
        'families_unchanged': True, 'successful_disclosures': sum(bool(r['branches']['known_production_then_inspect']['terminal_missing_recipes_revealed']) for r in records)}
    atomic_json(OUT/'knowledge_counterfactuals.json', result)
    print(json.dumps({'records': len(records), 'successful_disclosures': result['successful_disclosures'], 'api_calls': 0}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); a = p.parse_args(); main(a.runtime)
