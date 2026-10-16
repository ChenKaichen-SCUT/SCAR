"""Small, predeclared diagnostic replay; no counterfactual reward evaluation.

Selection reads only step/action/current-observation. Next observations are released
to each monitor ONLY after its prediction has been written to disk. The replay
driver retains the held-out outcome; neither learner nor planner receives it.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from scar_public.causal_model import CausalMonitor, ProposalError, request_proposal, digest
from scar_public.causal_compiler import fragment_check
from scar_public.provider import Provider, usage_summary


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def code_hashes():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
            ('causal_model.py', 'causal_compiler.py', 'replay_causal.py', 'finite_planner.py')}


def select(rows):
    selected = {}
    for prefix in ('enter ', 'pick up ', 'craft ', 'write '):
        row = next((r for r in rows if r['action'].startswith(prefix)
                    and 'Current Location: Tutorial,' not in r['observation']), None)
        if row:
            selected[row['step']] = 'first outside tutorial: ' + prefix.strip()
    row = next((r for r in rows if r['step'] >= 150 and r['action'].startswith('craft ')), None)
    if row:
        selected[row['step']] = 'first craft at/after step 150'
    return selected


def build_prefix(rows, stop):
    monitor = CausalMonitor()
    for i, row in enumerate(rows[:stop+1]):
        if i and row['observation'] != rows[i-1]['next_observation']:
            raise ValueError('Discontinuous public trace')
        monitor.observe(row['observation'], rows[i-1]['action'] if i else None)
    return monitor


def run_case(game, rows, index, reason, args):
    row = rows[index]
    directory = Path(args.output) / f'{game}-{row["step"]:04d}'
    final = directory / 'result.json'
    source_hash = digest([{k: r[k] for k in ('step', 'observation', 'action', 'next_observation')} for r in rows])
    if final.exists():
        previous = json.loads(final.read_text(encoding='utf-8'))
        if previous['source_hash'] != source_hash or previous.get('code_hashes') != code_hashes():
            raise ValueError('Source or adapter changed; use a new output directory')
        return previous
    monitor = build_prefix(rows, index)
    provider = Provider(directory / 'api', args.key, args.model)
    provider.step = row['step']
    record = {'game': game, 'step': row['step'], 'action': row['action'], 'selection': reason,
              'source_hash': source_hash, 'code_hashes': code_hashes(), 'phases': []}

    def phase(label, current_row):
        entry = {'phase': label, 'step': current_row['step'], 'action': current_row['action'],
                 'context_hash': digest(monitor.context(current_row['action'])),
                 'prefix_hash': monitor.prefix_hash, 'prefix_observations': len(monitor.observations)}
        try:
            entry['proposal'], _ = request_proposal(provider, monitor, current_row['action'])
            entry['accepted'] = True
        except ProposalError as error:
            entry.update(accepted=False, schema_error=str(error))
        except RuntimeError as error:
            entry.update(accepted=False, provider_error=str(error))
        entry['fragment'] = fragment_check(monitor, current_row['action'])
        entry['admission'] = [c for c in monitor.admission_checks if c['prefix_hash'] == monitor.prefix_hash
                              and c['action'] == current_row['action']]
        entry['prediction'] = monitor.prepare(current_row['action'])
        # This file is committed before the actual outcome enters the monitor.
        save(directory / (label + '.prediction.json'), entry)
        entry['feedback'] = monitor.observe(current_row['next_observation'], current_row['action'])
        entry['model_version_after_feedback'] = monitor.version
        record['phases'].append(entry)
        return any(c['verdict'] == 'contradicted' for c in entry['feedback']['checks'])

    contradicted = phase('initial', row)
    if contradicted:
        # At most ONE repair per case, evaluated only at a real repeated command.
        following = next((j for j in range(index+1, min(len(rows), index+31))
                          if rows[j]['action'] == row['action']), None)
        if following is not None:
            for j in range(index+1, following):
                monitor.observe(rows[j]['next_observation'], rows[j]['action'])
            assert monitor.observations[-1] == rows[following]['observation']
            provider.step = rows[following]['step']
            phase('repair', rows[following])
        else:
            record['repair_not_evaluated'] = 'no repeated identical command in next 30 recorded actions'
    record['final_model'] = monitor.state()
    record['usage'] = usage_summary(directory / 'api')
    save(final, record)
    print(json.dumps({'case': directory.name, 'phases': len(record['phases']),
                      'accepted': [p['accepted'] for p in record['phases']],
                      'feedback': [[c['verdict'] for c in p['feedback']['checks']] for p in record['phases']]}), flush=True)
    return record


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--public', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--key', required=True)
    p.add_argument('--model', default='deepseek-flash')
    p.add_argument('--workers', type=int, default=4)
    args = p.parse_args()
    if not 1 <= args.workers <= 64:
        p.error('workers must be 1..64')
    jobs = []
    sources = {}
    for game in ('remnant', 'mark', 'metropolis'):
        path = Path(args.public) / (game + '.public.json')
        rows = json.loads(path.read_text(encoding='utf-8'))
        sources[game] = {'steps': len(rows), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for step, reason in sorted(select(rows).items()):
            index = next(i for i, r in enumerate(rows) if r['step'] == step)
            jobs.append((game, rows, index, reason, args))
    plan = {'selection': 'first each of enter/pickup/craft/write outside Tutorial; first craft >=150',
            'repair': 'one per contradicted case, next identical action within 30 steps',
            'max_calls': 2*len(jobs), 'workers': args.workers, 'sources': sources, 'code_hashes': code_hashes(),
            'cases': [{'game': g, 'step': rows[i]['step'], 'action': rows[i]['action'], 'reason': reason}
                      for g, rows, i, reason, _ in jobs],
            'interpretation': 'development diagnostics; no performance/causality estimate'}
    save(Path(args.output) / 'selection.json', plan)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda job: run_case(*job), jobs))
    phases = [p for r in results for p in r['phases']]
    from collections import Counter
    summary = {'selection': plan, 'cases': len(results), 'phases': len(phases),
               'accepted': sum(p['accepted'] for p in phases),
               'hypothesis_verdicts': dict(Counter(c['verdict'] for p in phases for c in p['feedback']['checks'])),
               'fragment_statuses': dict(Counter(p['fragment']['status'] for p in phases)),
               'admission_statuses': dict(Counter(c['status'] for p in phases for c in p['admission'])),
               'usage': usage_summary(Path(args.output)),
               'cases_compact': [{k: r[k] for k in ('game', 'step', 'action', 'selection', 'phases', 'usage')} for r in results]}
    save(Path(args.output) / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('selection', 'cases_compact')}), flush=True)


if __name__ == '__main__':
    main()
