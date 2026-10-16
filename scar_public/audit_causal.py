"""Zero-API reproduction of frozen causal proposals and their planning results."""
import argparse
import json
from pathlib import Path

from scar_public.causal_model import digest
from scar_public.causal_compiler import fragment_check
from scar_public.replay_causal import build_prefix, code_hashes
from scar_public.finite_planner import run_checks


def audit(summary, public_directory):
    # A complete published report wraps the revised replay summary.
    summary = summary.get('revised_diagnostic', summary)
    count = 0
    for case in summary['cases_compact']:
        path = Path(public_directory)/f'{case["game"]}.public.json'
        rows = json.loads(path.read_text(encoding='utf-8'))
        monitor = build_prefix(rows, case['step']-1)
        for phase in case['phases']:
            while len(monitor.actions) < phase['step']-1:
                row = rows[len(monitor.actions)]
                monitor.observe(row['next_observation'], row['action'])
            row = rows[phase['step']-1]
            assert monitor.observations[-1] == row['observation']
            context = monitor.context(row['action'])
            assert digest(context) == phase['context_hash']
            if phase['accepted']:
                monitor.install(phase['proposal'], context)
            fragment = fragment_check(monitor, row['action'])
            assert monitor.prepare(row['action']) == phase['prediction']
            assert monitor.observe(row['next_observation'], row['action']) == phase['feedback']
            assert fragment == phase['fragment']
            count += 1
    core = run_checks()
    return {'api_calls': 0, 'frozen_phases_reproduced': count,
            'all_context_hashes_predictions_feedback_and_compiler_results_match': True,
            'final_code_hashes': code_hashes(),
            'core_checks': {k: core[k] for k in ('checked_instance_horizon_pairs', 'additional_budget_checks',
                'all_exact_search_values_match_unpruned_oracle',
                'all_finite_returned_policies_replayed_in_all_initial_worlds')}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', required=True)
    parser.add_argument('--public', required=True)
    parser.add_argument('--output')
    args = parser.parse_args()
    result = audit(json.loads(Path(args.summary).read_text(encoding='utf-8')), args.public)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
