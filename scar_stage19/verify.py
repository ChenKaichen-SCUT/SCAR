"""Independent post-freeze, offline archive audit; never calls the decision policy.

Reconstructs public knowledge from the actual public prefix and observations,
cross-checks native replay receipts, strict requests, ledger, intent lifecycles,
and rederived performance totals. Does not repair or resample model outputs.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess

from .common import ROOT, RESULTS, REPORTS, ENGINE_COMMIT, load, write, read_gzip, sha, deny_network
from .planning import FIELDS, SYSTEM, validate
from scar.io import digest
from scar_stage14.knowledge import Knowledge
from scar_v3.state import PublicState, parse_action


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (a, b)


def semantic(facts):
    return {k: {f: v.get(f) for f in ('ingredients', 'quantities', 'stations', 'certainty')}
            for k, v in facts.items()}


def ledger_snapshot(path):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
        return db.execute('SELECT id,reserved,charged,status FROM requests ORDER BY id').fetchall()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', type=Path, default=ROOT/'runtime/stage19')
    parser.add_argument('--key-path', type=Path, default=ROOT.parent/'miyao.txt')
    args = parser.parse_args()
    deny_network()
    ledger_before = ledger_snapshot(args.runtime/'budget.sqlite')
    freeze = load(RESULTS/'freeze.json')
    prior = load(RESULTS/'prior_manifest.json')['files']
    for paths in (freeze['files'], prior):
        for name, expected in paths.items():
            assert sha(ROOT/name) == expected, name
    assert freeze['site'] == 'local' and freeze['worker_processes'] == 12
    assert freeze['methods'] == ['SCAR19'] and freeze['max_steps'] == freeze['internal_P3_horizon'] == 100
    frozen_at = datetime.fromisoformat(freeze['created_utc']).timestamp()
    engine = Path(os.environ['AGENTODYSSEY_ROOT'])
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=engine, text=True).strip() == ENGINE_COMMIT
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=engine, text=True).strip()
    tasks = load(RESULTS/'tasks.json')
    assert tasks == load(ROOT/'results/stage17/tasks.json') and len(tasks) == 24
    assert Counter(t['game_name'] for t in tasks) == {'robot_kingdom': 15, 'quarantine': 9}
    assert sha(RESULTS/'initial_public_histories.jsonl.gz') == sha(ROOT/'results/stage17/initial_public_histories.jsonl.gz')
    histories = {h['task_id']: h for h in read_gzip(RESULTS/'initial_public_histories.jsonl.gz')}
    assert {p.name for p in (RESULTS/'runs').iterdir() if p.is_dir()} == {t['task_id']+'__SCAR19' for t in tasks}
    replay = load(RESULTS/'replay_local.json')
    assert replay['passed'] and replay['new_api_calls'] == 0 and replay['trajectory_count'] == 24
    replay_by_id = {r['task_id']: r for r in replay['runs']}
    stats = {(r['task_id'], r['method']): r for r in load(RESULTS/'per_task.json')}
    assert len(stats) == 168
    for old in load(ROOT/'results/stage18/per_task.json'):
        archived = stats[old['task_id'], old['method']]
        for key, value in old.items():
            assert archived[key] == value, (old['task_id'], old['method'], key)
    intents = {(r['task_id'], r['id']): r for r in load(RESULTS/'subgoal_outcomes.json')}
    totals = Counter(); checks = []; all_requests = {}; all_ends = {}; finish_reasons = Counter()
    summary_snapshot_differences = []
    for task in tasks:
        tid = task['task_id']; folder = RESULTS/'runs'/f'{tid}__SCAR19'
        summary = load(folder/'summary.json')
        rows = read_gzip(folder/'trajectory.jsonl.gz')
        requests = read_gzip(folder/'requests.jsonl.gz')
        assert len(rows) == summary['steps'] <= 100
        assert summary['method'] == 'SCAR19' and summary['task_id'] == tid
        assert summary['initial_state_hash'] == task['initial_state_hash']
        assert summary['started'] >= frozen_at
        assert digest(histories[tid]['history']) == task['initial_public_history_hash']
        knowledge = Knowledge()
        for h in histories[tid]['history']:
            knowledge.observe(h['after'], h['action'], cutoff=h['after']['step'])
        knowledge.observe(rows[0]['observation'], None, cutoff=rows[0]['observation']['step'])
        by_step = defaultdict(list); logical = defaultdict(list); count = Counter()
        for q in requests:
            assert q['request_id'] not in all_requests
            all_requests[q['request_id']] = q
            by_step[q['step']].append(q); logical[q['logical_id']].append(q)
            assert q['start'] >= frozen_at and q['end'] >= q['start']
            assert q['phase'] == 'subgoal' and q['ordinal'] == 1 and 0 <= q['attempt'] < 3
            assert q['logical_id'] == f"{q['step']:03d}:001"
            assert q['model'] == 'deepseek-flash' and q['temperature'] == .7 and q['thinking'] == 'disabled'
            assert q['max_tokens'] == 768 and 1 <= q['step'] <= len(rows)+1
            assert q['messages'][0] == {'role': 'system', 'content': SYSTEM}
            assert q['signature'] == digest(dict(messages=q['messages'], phase=q['phase'], max_tokens=768, required=FIELDS))
            usage = q['usage']; assert usage == q['raw_response']['usage']
            assert usage['total_tokens'] == usage['prompt_tokens']+usage['completion_tokens']
            price = freeze['model_config']['pricing_usd_per_million']
            charge = (usage['prompt_cache_hit_tokens']*price['cache_hit'] +
                      (usage['prompt_tokens']-usage['prompt_cache_hit_tokens'])*price['cache_miss'] +
                      usage['completion_tokens']*price['output'])/1e6
            close(charge, q['cost_usd']); close(charge, q['charged_or_reserved_usd'])
            count['cost_usd'] += charge
            count['input_tokens'] += usage['prompt_tokens']; count['output_tokens'] += usage['completion_tokens']
            finish_reasons[q['raw_response']['choices'][0]['finish_reason']] += 1
            raw = q['raw_response']['choices'][0]['message']['content']
            try:
                parsed = json.loads(raw); validate(parsed)
                valid = True
            except (ValueError, TypeError):
                valid = False
            assert valid == (q['status'] == 'ok')
            if valid:
                assert parsed == q['parsed'] and 'action' not in parsed
            else:
                assert q['status'] == 'invalid_response'
            count['api_failed_requests'] += not valid
        for group in logical.values():
            assert [q['attempt'] for q in group] == list(range(len(group)))
            assert len({q['signature'] for q in group}) == 1 and len(group) <= 3
            assert not any(q['status'] == 'ok' for q in group[:-1])
        assert len(logical) <= freeze['max_logical_calls_per_episode']
        assert count['cost_usd'] <= freeze['model_config']['episode_budget_usd']
        count['api_calls'] = len(requests); count['logical_subgoal_requests'] = len(logical)
        last_hash = task['initial_state_hash']; inspected = Counter(); ends = {}; accepted = set()
        persistent_steps = Counter(); previous_feedback = None
        for step, row in enumerate(rows, 1):
            assert row['step'] == step and row['seed'] == task['initial_seed'] and row['goal'] == task['objective_text']
            assert row['method'] == 'SCAR19' and row['task_id'] == tid
            assert row['physical_before']['state_hash'] == last_hash
            if previous_feedback is not None: assert row['observation'] == previous_feedback
            previous_feedback = row['feedback']; last_hash = row['state_hash']
            assert row['physical_after']['state_hash'] == last_hash
            success = (row['physical_after']['target_owned'] >= task['target_amount'] and
                       row['target_produced_during_task'] >= task['target_amount'])
            assert success == row['success']
            if step < len(rows): assert not row['success'] and not row['done'] and not row['death']
            assert knowledge.view() == row['public_knowledge_before']
            d = row['decision']['decision']; controller = row['decision']['controller']
            assert semantic(controller['table']['knowledge']['facts']) == semantic(knowledge.view())
            assert controller['target'] == d['controller_before']['target'] == 'craft 1 '+task['target_item']
            assert controller['step16'] == step-1
            assert d['executed_action'] == row['action'] and d['no_action_proposal_interface']
            assert not any('consequence' in k.lower() for k in controller)
            assert d['stage19']['original_task'] == controller['target'] and d['stage19']['internal_horizon'] == 100
            transaction = d['stage19']['transaction']
            assert transaction['exploration_after']-transaction['exploration_before'] == bool(transaction['executed_probe'])
            assert transaction['failures_unchanged'] and transaction['attempts_unchanged']
            assert controller['exploration_spent'] == transaction['exploration_after']
            successful = [q for q in by_step[step] if q['status'] == 'ok']
            assert len(successful) == int(d['llm_called'])
            if d['llm_called']:
                assert successful[0]['parsed'] == d['subgoal_proposal'] and d['planning_trigger']
                fs = d['fact_summary']; assert len(fs['records']) <= 48 and fs['characters'] <= 6000
                prompt = successful[0]['messages'][-1]['content']
                assert fs['prompt_characters'] == len(prompt) and row['observation']['text'] in prompt
                raw_facts = prompt.split('STRUCTURED PUBLIC EVIDENCE:\n', 1)[1]
                prompt_records = [json.loads(line) for line in raw_facts.splitlines()]
                assert fs['characters'] == len(raw_facts) and len(prompt_records) == len(fs['records'])
                # render() kept mutable table values in its secondary summary.
                # The provider saved the original literal prompt. Audit and use
                # that original; do not silently overwrite frozen raw artifacts.
                for original, saved in zip(prompt_records, fs['records']):
                    if original == saved: continue
                    assert original['id'] == saved['id'] and original['id'].startswith('recipe19:')
                    assert {k:v for k,v in original.items() if k != 'value'} == {k:v for k,v in saved.items() if k != 'value'}
                    a, b = original['value'], saved['value']
                    changed = [k for k in set(a)|set(b) if a.get(k) != b.get(k)]
                    assert set(changed) <= {'source', 'step', 'ingredients'}
                    assert set(a.get('ingredients') or []) == set(b.get('ingredients') or [])
                    summary_snapshot_differences.append(dict(task_id=tid, step=step, record_id=original['id'],
                        changed_fields=sorted(changed), original_request_record=original, secondary_summary_record=saved,
                        knowledge_content_changed=False))
                for record in prompt_records:
                    if record['id'].startswith('recipe19:'):
                        actual = knowledge.facts[record['key']]; visible = record['value']
                        assert set(visible.get('ingredients') or []) == set(actual.get('ingredients') or [])
                        assert visible.get('quantities') == actual.get('quantities')
                        assert set(visible.get('stations') or []) == set(actual.get('stations') or [])
                if d['subgoal_acceptance']['accepted']:
                    assert all(e in prompt for e in d['subgoal_proposal']['public_evidence'])
                    ident = d['subgoal_acceptance']['intent_id']; assert ident not in accepted
                    accepted.add(ident)
            else:
                assert not by_step[step] and d['subgoal_proposal'] is None
            outcome = row['mechanism_outcome']; assert outcome['action'] == row['action']
            for end in controller.get('intent_log19', [])+outcome['latest_intent_end']:
                assert end['final_goal_unchanged']; ends[end['id']] = end
            if d['stage19']['source'] == 'persistent_subgoal':
                persistent_steps[d['active_subgoal']['id']] += 1
            delta = knowledge.observe(row['feedback'], row['action'], cutoff=row['feedback']['step'], source={'evaluation_step': step})
            assert delta == row['knowledge_delta'] and knowledge.view() == row['public_knowledge_after']
            for fact in knowledge.facts.values(): assert fact['observed_step'] <= row['feedback']['step']
            for key, pre in outcome['preconditions'].items():
                observed = rows[pre['first_step']-1]
                assert pre['source'] == 'native_missing_necessary_feedback' and pre['object_type'] == 'UNKNOWN'
                assert pre['raw_feedback'] == observed['mechanism_outcome']['feedback']
                pattern = r'Cannot craft '+re.escape(pre['product'])+r'\. Missing necessary (.+?) in the current area\.'
                match = re.search(pattern, pre['raw_feedback'])
                assert match and pre['required_object'] in match[1].split(', ')
                assert key == pre['product']+':'+pre['required_object']
                if pre['first_satisfied_step'] is not None:
                    ground = PublicState.observe(rows[pre['first_satisfied_step']-1]['feedback']).ground
                    assert ground and ground.get(pre['required_object'], 0) > 0
            p = parse_action(row['action']); m = row['metrics']
            count['steps'] += 1; count['controller_only_actions'] += not d['llm_called']
            count['controller_only_nonwait_actions'] += not d['llm_called'] and p.verb != 'wait'
            count['wait_actions'] += p.verb == 'wait'
            count['craft_attempts'] += p.verb == 'craft'; count['productive_crafts'] += bool(m['actual_production'])
            for field in ('craft_failed', 'material_rejection', 'station_rejection', 'invalid'): count[field] += bool(m[field])
            if p.verb == 'inspect':
                count['repeated_inspections'] += inspected[p.target] > 0; inspected[p.target] += 1
        assert summary['final_state_hash'] == last_hash and summary['success'] == rows[-1]['success']
        assert set(ends) == accepted
        for ident, end in ends.items():
            saved = intents[tid, ident]
            assert all(saved[k] == v for k, v in end.items())
            assert saved['steps'] == persistent_steps[ident]
            all_ends[tid, ident] = end
        if summary['status'] == 'model_parse_exception':
            assert len(by_step[len(rows)+1]) == 3 and all(q['status'] != 'ok' for q in by_step[len(rows)+1])
        else:
            assert not by_step[len(rows)+1]
            assert summary['status'] == ('success' if summary['success'] else
                'game_failure' if rows[-1]['done'] or rows[-1]['death'] or rows[-1]['physical_after']['health'] <= 0 else 'step_limit')
            if summary['status'] == 'step_limit': assert len(rows) == 100
        native = replay_by_id[tid]
        assert native['passed'] and native['final_hash'] == last_hash and native['true_success'] == summary['success']
        assert native['steps'] == len(rows) and native['requests'] == len(requests)
        for key, value in count.items(): close(value, stats[tid, 'SCAR19'].get(key, 0))
        count['success'] = summary['success']
        for b in (60, 80, 100): count['R'+str(b)] = summary['success'] and len(rows) <= b
        totals.update(count)
        checks.append(dict(task_id=tid, passed=True, actions=len(rows), requests=len(requests),
                           final_hash=last_hash, true_success=summary['success'], status=summary['status']))
    assert set(intents) == set(all_ends)
    assert sum(r['steps'] for r in all_ends.values()) == 101
    assert replay['real_replay_actions'] == totals['steps']
    ledger = load(RESULTS/'cost_ledger.json')
    assert {r['request_id'] for r in ledger['requests']} == set(all_requests)
    sqlite_rows = {r[0]: r for r in ledger_before}; assert set(sqlite_rows) == set(all_requests)
    for r in ledger['requests']:
        q = all_requests[r['request_id']]; db = sqlite_rows[r['request_id']]
        close(r['charged_usd'], q['charged_or_reserved_usd']); close(r['reserved_usd'], q['reserved_usd'])
        assert r['status'] == q['status'] == db[3]; close(db[1], r['reserved_usd']); close(db[2], r['charged_usd'])
    close(ledger['committed_usd'], totals['cost_usd'])
    assert totals['cost_usd'] <= freeze['model_config']['total_budget_usd']
    analysis = load(RESULTS/'analysis.json')['methods']['SCAR19']
    for key, value in totals.items(): close(value, analysis[key])
    assert len(read_gzip(RESULTS/'evidence_index.jsonl.gz')) == totals['steps']
    assert len(load(RESULTS/'response_errors.json')) == totals['api_failed_requests']
    assert len(load(RESULTS/'failures.json')) == 24-totals['success']
    preflight = load(RESULTS/'preflight_local.json'); assert preflight['passed'] and preflight['api_calls'] == 0
    assert len(list(REPORTS.glob('*.md'))) >= 9
    # Sensitive byte matching stays in memory. Nothing prints or archives the key.
    secrets = []
    if args.key_path.exists():
        raw_key = args.key_path.read_bytes().strip()
        secrets = re.findall(rb'sk-[A-Za-z0-9_-]{16,}', raw_key)
        if raw_key: secrets.append(raw_key)
    published = [p for d in (ROOT/'scar_stage19', RESULTS, REPORTS) for p in d.rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    published.append(ROOT/'scripts/run_stage19.sh')
    for p in published:
        raw = gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes()
        assert not any(s in raw for s in secrets), 'Secret found in '+str(p.relative_to(ROOT))
        assert not re.search(rb'(?i)Bearer\s+sk-[A-Za-z0-9_-]{16,}', raw), str(p)
        assert p.stat().st_size < 100*1024*1024, str(p)
    assert ledger_snapshot(args.runtime/'budget.sqlite') == ledger_before
    write(RESULTS/'context_snapshot_audit.json', dict(
        canonical_source='literal messages in requests.jsonl.gz, before response and second choose',
        differing_request_steps=len({(d['task_id'], d['step']) for d in summary_snapshot_differences}),
        differing_records=len(summary_snapshot_differences), knowledge_content_changed=False,
        limitation='Secondary fact_summary records alias controller tables; source labels, last-observed metadata and ingredient ordering may mutate during choose. Raw model prompts remain authoritative.',
        evidence=summary_snapshot_differences))
    receipt = dict(passed=True, verified_utc=datetime.now(timezone.utc).isoformat(), site='local',
        independent_process=True, network_disabled=True, new_api_calls=0, policy_decisions_reexecuted=0,
        native_replay_receipt='results/stage19/replay_local.json', native_replay_actions=totals['steps'],
        frozen_files_verified=len(freeze['files']), historical_files_unchanged=len(prior),
        source_engine_commit=ENGINE_COMMIT, public_knowledge_reconstructed_actions=totals['steps'],
        checkpoints='native state hashes validated by full replay; public knowledge rederived here',
        request_schema_and_usage_verified=len(all_requests), cost_usd=totals['cost_usd'],
        request_finish_reasons=dict(finish_reasons), final_goals_preserved=True,
        secondary_summary_snapshot_differences=len({(d['task_id'], d['step']) for d in summary_snapshot_differences}),
        canonical_model_context='literal archived requests, not post-choose summary references',
        accepted_intent_lifecycles_verified=len(intents), matched_shared_sqlite_ledger=True,
        secrets_scan_passed=True, raw_secret_logged=False, failed_episodes_resampled=0,
        historical_baseline_runs_added=0, runs=checks, totals=dict(totals))
    write(RESULTS/'verification.json', receipt)
    write(RESULTS/'research_state.json', dict(phase='complete_local_verified', formal_started=True,
        total_runs=24, archived_runs=24, success=totals['success'], new_api_requests=totals['api_calls'],
        cost_usd=totals['cost_usd'], native_replay_passed=True, independent_verification_passed=True,
        no_further_experiments=True, policy_unchanged_after_freeze=True))
    published += [RESULTS/'verification.json', RESULTS/'research_state.json', RESULTS/'context_snapshot_audit.json']
    manifest = {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(published))
                if p.name != 'artifact_manifest.json'}
    write(RESULTS/'artifact_manifest.json', dict(files=manifest, includes_analysis_and_reports=True,
        excludes=['this self-referential manifest', 'downloaded dependencies', 'private runtime/checkpoints', 'credentials']))
    print(json.dumps(dict(passed=True, runs=24, actions=totals['steps'], requests=totals['api_calls'],
                          cost_usd=totals['cost_usd'], historical_files=len(prior), artifacts=len(manifest))))


if __name__ == '__main__':
    main()
