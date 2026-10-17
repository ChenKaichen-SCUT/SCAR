"""Post-study audit of executed gates and mechanism exposure; no API requests.

Immediate failure/reward-after-intervention counts are descriptive, not a
counterfactual estimate of the value of that individual intervention.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics

from scar_public.core_planner import gate


def audit(root):
    analysis = json.loads((root/'analysis.json').read_text())
    episodes = []; paired_calls=[]
    for block in analysis['blocks']:
        name = f"{block['game']}_r{block['repeat']}"
        calls={}
        for line in (root/'evaluation'/name/'calls.jsonl').read_text().splitlines():
            call=json.loads(line)
            calls.setdefault((call['arm'],call['step']),[]).append(
                (call['prompt_sha256'],call['response_sha256']))
        first=block['prefix_audit']['first_action_difference']
        prefix=first['step'] if first else block['arms']['prompt']['steps']
        count=0
        for step in range(prefix):
            assert calls['prompt',step]==calls['checked',step], (name,step,'different actor calls before action divergence')
            count+=len(calls['prompt',step])
        paired_calls.append(dict(block=name,matched_decision_steps=prefix,matched_actor_calls=count,mismatches=0))
        for arm in ('prompt', 'checked', 'sentry'):
            path = root/'evaluation'/name/arm
            traces = [json.loads(p.read_text()) for p in sorted((path/'trace').glob('*.json'))]
            reasons = Counter(); status = Counter(); observed = Counter()
            candidate_rejections = Counter(); evidence_revisions = 0
            overrides = []; timings = []
            for row in traces:
                response = json.loads(row['response'])
                packet, record = response['core_packet'], response['core_gate']
                replay = gate(packet, {'action': record['proposed']},
                              'checked' if arm == 'checked' else 'prompt', packet['guard'])
                assert replay['action'] == row['action'], (name, arm, row['step'])
                assert replay['core_gate'] == record, (name, arm, row['step'], 'gate')
                reasons[record['reason']] += 1
                observed[packet['observed_check']['status']] += 1
                for item in packet['rejected']:
                    for reason in item.get('reasons', [item.get('reason', 'unspecified')]):
                        candidate_rejections[reason] += 1
                candidate = packet['recommendation']
                if candidate:
                    checks = candidate['gate_obligations']
                    assert candidate['role_supported']
                    assert candidate['reserve']['status'] in ('NO_OTHER_EXPLICIT_OUTPUTS', 'JOINT_WITNESS_RETAINED')
                    assert checks['first_action']['status'] != 'contradicted'
                    assert checks['plan_cost'] <= checks['remaining_budget']
                    assert candidate in packet['candidates']
                    status[candidate['reserve']['status']] += 1
                if record['changed']:
                    assert arm == 'checked' and candidate
                    assert row['action'] == candidate['plan'][0]
                    overrides.append(dict(step=row['step'],proposed=record['proposed'],
                        initial_proposed=packet['proposal'],
                        actor_revised_action=packet['proposal']!=record['proposed'],
                        explicit_failure_support_for_final=(packet['proposal']==record['proposed'] and
                            (packet['observed_check']['status']=='contradicted' or bool(packet['evidence_rejection']))),
                        executed=row['action'],task=candidate['task'],endpoint=candidate['endpoint'],
                        role=candidate['support'],reserve_status=candidate['reserve']['status'],
                        first_check=checks['first_action']['status'],
                        evidence_rejection=bool(packet['evidence_rejection']),
                        immediate_cannot='Cannot ' in row['next_observation'],
                        feedback=row['next_observation'],
                        packet_id=packet['id']))
                evidence_revisions += bool(packet['evidence_rejection'])
                timings.append(response['core_compute_ms'])
            checkpoint = path/'checkpoints'/f'{len(traces):04d}'/'agent.json'
            bank = json.loads(checkpoint.read_text())['resource_evidence']
            events = bank['audit']
            episodes.append(dict(block=name,arm=arm,steps=len(traces),gate_reasons=dict(reasons),
                reserve_statuses_of_recommendations=dict(status),observed_action_checks=dict(observed),
                candidate_rejections=dict(candidate_rejections),evidence_rejection_packets=evidence_revisions,
                evidence_matched_transitions=sum(e['kind'] in ('MATCHED_TRANSITION','PASSIVE_MATCHED_TRANSITION') for e in events),
                evidence_shrinking_transitions=sum(e['kind'] in ('MATCHED_TRANSITION','PASSIVE_MATCHED_TRANSITION') and e['after']<e['before'] for e in events),
                evidence_revocations=sum(e['kind']=='REVOKED' for e in events),
                evidence_contexts=len(bank['contexts']),overrides=overrides,
                planner_ms_median=statistics.median(timings),planner_ms_max=max(timings)))
    result=dict(episodes=episodes,paired_call_audit=paired_calls,gate_replay_mismatches=0,
                checked_transitions=sum(e['steps'] for e in episodes),
                interpretation='Descriptive exposure and code-path audit, not causal attribution per override; formal paired outcomes are in analysis.json.')
    (root/'mechanism_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(gate_replay_mismatches=0,checked_transitions=result['checked_transitions'],
        overrides=sum(len(e['overrides']) for e in episodes),
        shrinking_transitions=sum(e['evidence_shrinking_transitions'] for e in episodes)),indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    audit(p.parse_args().root)
