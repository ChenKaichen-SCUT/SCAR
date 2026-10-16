"""Validate the bounded V6 development study without rerunning any policy."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from scar.environment import restore, state_digest, AGENT_ID
from scar_public.obligation_agent import ObligationMemory
from scar_public.obligations import ExecutionModel, explicit_role_bindings, words
from scar_public.provider import usage_summary
from scar_public.summarize import summarize


def audit_semantic_opportunities(rows):
    """Replay public observations only; count scheduler prerequisites separately."""
    model=ExecutionModel()
    counts=Counter()
    goals=set()
    writes=[]
    eligible=[]
    previous=None
    for row in rows:
        model.observe(row['observation'],previous)
        previous=row['action']
        pending=[g for g in model.tasks if re.search(r'\b(record|write|inscribe|copy)\b',g,re.I)]
        if pending:counts['steps_with_pending_writing_goal']+=1
        goals.update(pending)
        held=model.current.get('holding') or {}
        if row['action'].startswith('write '):
            payload,name=row['action'][6:].rsplit(' ',1)
            doc=model.documents.get(name,{})
            writes.append({'step':row['step'],'document':name,'payload':payload,
                          'fresh_text_before':doc.get('text') if doc.get('observed_at')==len(model.history)-1 else None,
                          'accepted':'I wrote on '+name+':' in row['next_observation']})
        stages=set()
        for goal in pending:
            binding=explicit_role_bindings(goal,model.source_lines)
            dest=re.search(r'\b(?:on|onto|in|into) (?:a |an |the )?(.+?)(?: so\b| to\b|[.!?]|$)',goal,re.I)
            if len(binding)!=1 or not dest:continue
            stages.add('steps_with_unique_literal_and_destination')
            docs=[n for n in held if words(n)==dest[1].strip().lower()]
            if not docs:continue
            stages.add('steps_with_matching_document_held')
            if not any(n in held for n in model.writing_tools):continue
            stages.add('steps_with_previously_observed_tool_held')
            if 'I was attacked' not in row['observation']:
                stages.add('steps_meeting_basic_scheduler_prerequisites')
                eligible.append({'step':row['step'],'goal':goal,'documents':docs,'literal':binding[0]['value'],
                                 'last_observed_text':{n:model.documents.get(n,{}).get('text') for n in docs}})
        counts.update(stages)
    return {'counts':dict(counts),'observed_writing_goals':sorted(goals),
            'actual_write_interventions':writes,'basic_eligibility_examples':eligible[:12],
            'scope':'Full-run public observations only; necessary eligibility stages, before duplicate/full-text suppression or workflow priorities. No hypothetical environment actions.'}


def inspect_run(run, expected=30):
    manifest=json.loads((run/'manifest.json').read_text())
    current=json.loads((run/'current.json').read_text())
    rows=[json.loads(p.read_text()) for p in sorted((run/'trace').glob('*.json'))]
    fork=manifest.get('diagnostic_fork')
    assert current['complete']
    assert len(rows)==expected or (len(rows)<expected and current['termination']=='environment' and rows[-1]['done'])
    first=fork['start_step'] if fork else 0
    assert [r['step'] for r in rows]==list(range(first+1,first+len(rows)+1))
    root=run.parents[2]
    source=Path(fork['path'])/'environment.pkl' if fork else root/'initial'/manifest['game']/'initial.pkl'
    before=restore(source,run/'validation_before')
    after=restore(run/'checkpoints'/current['checkpoint']/'environment.pkl',run/'validation_after')
    assert state_digest(before)==rows[0]['before_digest']
    assert state_digest(after)==rows[-1]['after_digest']
    assert after.scores[AGENT_ID]==current['scores']==rows[-1]['scores']
    assert manifest['enable_obs_valid_actions'] is False
    memory=ObligationMemory()
    memory.load(json.loads((run/'checkpoints'/current['checkpoint']/'agent.json').read_text()))
    policy_trials=[t for t in memory.model.semantic_trials if t['step']>=first]
    # The last public observation is available for evaluation after the final action,
    # even though no further policy decision is permitted by the action budget.
    memory.prompt(rows[-1]['next_observation'])
    operation_trials=[t for t in memory.model.semantic_trials if t['step']>=first]
    parsed=[json.loads(r['response']) for r in rows]
    source_counts=Counter(p.get('decision_source','actor') for p in parsed)
    initial=before.scores.get(AGENT_ID,{}).get('quest',0)
    contracts=[p.get('goal_contract',{}) for p in parsed]
    sample_steps={62:[63,64,65],172:[173,174,175,176],178:[179,180,181,182],138:[139,140,141]}.get(first,[])
    samples=[{**{k:r[k] for k in ('step','observation','action','next_observation','scores')},'response':p}
             for r,p in zip(rows,parsed) if r['step'] in sample_steps]
    result={'manifest':manifest,'actions':len(rows),'termination':current['termination'],
        'final_public_observation':rows[-1]['next_observation'],'main_before':initial,'main_after':current['scores']['quest'],
        'delta':current['scores']['quest']-initial,'sources':dict(source_counts),
        'operation_trials':operation_trials,'operation_trials_observed_before_last_action':len(policy_trials),
        'binding_trials':memory.binding_trials,'active_write_selections':memory.active_write_attempts,
        'recipe_counterexamples':memory.model.recipe_counterexamples,
        'failed_route_observations':len(memory.model.blocked_routes),
        'goal_contract_coverage':{'grounded':sum(bool(c.get('source_grounded')) for c in contracts),
            'with_supported_literals':sum(bool(c.get('supported_literals')) for c in contracts),
            'literal_count':sum(len(c.get('supported_literals',[])) for c in contracts)},
        'stagnant_two_move_cycle_steps':sum(i>=2 and rows[i]['action'].startswith('enter ') and
            rows[i]['action']==rows[i-2]['action'] and rows[i-1]['action'].startswith('enter ') and
            rows[i]['scores']['quest']==rows[i-2]['scores']['quest'] for i in range(len(rows))),
        'action_trace':[{'step':r['step'],'action':r['action'],'main':r['scores']['quest'],
            'source':p.get('decision_source','actor'),'supported_terminal_literals':p.get('goal_contract',{}).get('supported_literals',[])}
                       for r,p in zip(rows,parsed)],'posthoc_examples':samples,'usage':usage_summary(run/'api')}
    if fork:
        control=Path(fork['path']).parents[1]
        control_rows=[json.loads((control/'trace'/f'{i:04d}.json').read_text()) for i in range(first+1,first+len(rows)+1)]
        assert control_rows[0]['before_digest']==rows[0]['before_digest']
        result['frozen_control']={'path':str(control),'main_after':control_rows[-1]['scores']['quest'],
            'note':'Stored continuation, shared start and action budget, not matched inference or a fresh replicate.'}
    else:
        result['semantic_opportunity_audit']=audit_semantic_opportunities(rows)
    return result


def analyze(root, full_required=True):
    root=Path(root)
    diagnostics=[inspect_run(p.parent) for p in sorted(root.glob('v6diag*/*/*/current.json'))]
    assert len(diagnostics)==8
    full={}
    for game in ('remnant','mark','metropolis'):
        run=root/'round7/obligation_v6'/game
        if (run/'current.json').exists() and json.loads((run/'current.json').read_text())['complete']:
            full[game]=inspect_run(run,300)
    if full_required:assert len(full)==3
    groups=summarize(root)['groups']
    # Repair the legacy summary's first-stage label when a method has multiple rounds.
    for method,group in groups.items():
        stages={g['manifest']['stage'] for g in group['games'].values()}
        if len(stages)==1:
            group['stage']=next(iter(stages));group['usage']=usage_summary(root/group['stage']/method)
    official=None
    if len(full)==3:
        command=[sys.executable,str(root.parent/'source/AgentOdyssey/challenge_eval.py'),'--json']
        for game in full:command+=['--'+game,str(root/'round7/obligation_v6'/game)]
        official=json.loads(subprocess.check_output(command))
        assert official['aggregate']['main_quest_mean']==groups['obligation_v6']['main_mean']
    frozen=json.loads((root/'frozen-baselines.json').read_text())
    for name,files in frozen.items():
        for filename,sha in files.items():assert hashlib.sha256((root/'round1'/name/filename).read_bytes()).hexdigest()==sha
    usage=[r['usage'] for r in diagnostics]+[r['usage'] for r in full.values()]
    current={k:sum(r[k] for r in usage) for k in ('requests','successful_responses','peak_usd_estimate',
        'unknown_charge_attempts','prompt_tokens','completion_tokens','cache_hit_tokens')}
    return {'diagnostics':diagnostics,'full_runs':full,'all_full_groups':groups,'official_v6':official,
        'new_phase_usage':current,'all_phases_usage':usage_summary(root),'frozen_baselines_verified':len(frozen),
        'limitations':'Selected development states and single full runs; coupled changes, unequal inference budgets, conservative incomplete goal grammar, conditional partial planning model. No statistical significance or novelty claim.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    p.add_argument('--diagnostics-only',action='store_true');args=p.parse_args()
    data=analyze(args.root,not args.diagnostics_only)
    Path(args.out).write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(json.dumps({'diagnostics':[(d['manifest']['stage'],d['main_before'],d['main_after'],len(d['operation_trials']),len(d['binding_trials'])) for d in data['diagnostics']],
                      'official':data['official_v6'],'new_usage':data['new_phase_usage'],'total_usage':data['all_phases_usage']},indent=2))
