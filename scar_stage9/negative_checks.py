"""Post-result diagnosis only: one action intervention, common evaluator suffix.

No policy changes or model calls. These are NOT autonomous recovery episodes.
"""
import argparse
import contextlib
import gzip
import hashlib
import json
from pathlib import Path
from scar.io import atomic_json
from scar_unknown17.audit import branch

OUT = Path('results/stage9')


def main(runtime):
    root = Path(runtime)
    cases = {c['id']: c for c in json.loads((OUT/'cases.json').read_text())}
    records = []
    with (root/'negative_checks.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for method in ['F1', 'F2']:
            for ep in map(json.loads, gzip.open(OUT/f'trajectories_{method}.jsonl.gz', 'rt')):
                case = cases[ep['case_id']]
                assert case['game'] == 'robot_kingdom'
                goal = case['goal']['name']
                if goal == 'bandage_roll':
                    index = next(r['index'] for r in ep['rows'] if r['executed_action'] == 'craft 1 sinew_cord' and not r['semantic_rejection'])
                    alternative = 'craft 2 sinew_cord'
                    suffix = ['store 2 sinew_cord inventory', 'enter cellar', 'enter barracks',
                        'store 1 salvage_cloth inventory', 'enter cellar', 'enter courtyard',
                        'craft 1 bandage_roll', 'store 2 bandage_roll inventory']
                    hypothesis = 'separate minimum batches consume two cloth units; a paired two-output batch can retain the final ingredient'
                elif goal == 'fiend_alloy_scale':
                    index = next(r['index'] for r in ep['rows'] if r['executed_action'] == 'store 1 brimite_ingot inventory')
                    alternative = 'store 2 brimite_ingot inventory'
                    suffix = [r['executed_action'] for r in ep['rows'][index+1:14]] + [
                        'enter cellar', 'store 1 hellcoal_concentrate inventory', 'enter courtyard',
                        'craft 1 fiend_alloy', 'store 1 fiend_alloy inventory', 'craft 1 fiend_alloy_sheet',
                        'store 1 fiend_alloy_sheet inventory', 'craft 1 fiend_alloy_scale', 'store 2 fiend_alloy_scale inventory']
                    hypothesis = 'collecting only current lower-bound demand leaves the second visible ingot exposed to real step-rule loss'
                else:
                    continue
                folder = root/'runs'/ep['task_id']
                raw = (folder/'initial.pkl' if index == 0 else folder/'steps'/f'{index:04}'/'environment.pkl').read_bytes()
                row = ep['rows'][index]
                assert index+len(suffix)+1 <= 40
                old = branch(raw, [row['executed_action']]+suffix, case)
                new = branch(raw, [alternative]+suffix, case)
                path = OUT/'diagnostic_states'/f'{ep["task_id"]}-{index}.pkl.gz'; path.parent.mkdir(exist_ok=True)
                with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as f: f.write(raw)
                records.append({'case_id': case['id'], 'method': method, 'index': index, 'task_id': ep['task_id'],
                    'state': {'path': str(path), 'serialized_sha256': hashlib.sha256(raw).hexdigest()},
                    'public_observation': row['observation'], 'public_controller': row['stage7_state_before'],
                    'original_action': row['executed_action'], 'alternative_action': alternative, 'common_suffix': suffix,
                    'original': old, 'alternative': new, 'hypothesis': hypothesis,
                    'improved_fixed_suffix': new['goal'] and not old['goal'], 'within40': True,
                    'scope': 'post-hoc evaluator-provided common continuation, each branch replayed twice; NOT agent success or a policy patch'})
    atomic_json(OUT/'negative_counterfactuals.json', {'records': records, 'api_calls': 0, 'policy_changed': False,
        'improvements': sum(r['improved_fixed_suffix'] for r in records), 'all_failures_retained': True})
    print(json.dumps([{'method': r['method'], 'case': r['case_id'], 'old': r['original']['goal'], 'alternative': r['alternative']['goal']} for r in records]))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime', required=True); a = p.parse_args(); main(a.runtime)
