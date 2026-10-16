"""Applicability audit on the same three publicly grounded local game models."""
from hashlib import sha256
import json
from pathlib import Path

from scar_public.audit_information_game_models import restore_problem
from scar_public.control_capacity import ControlCapacity
from scar_public.finite_planner import printable
from scar_public.information_transfer import TransferInstance
from scar_public.resource_competition import compile_resources
from scar_public.study_control_capacity import measure, projections


def main():
    source=Path(__file__).parent/'results/2026-10-16-resource-competition/analysis.json'
    saved=json.loads(source.read_text(encoding='utf-8'))
    rows=[]
    for record in saved['cases']:
        compiled=compile_resources(restore_problem(record['selection']['grounding']),
                                   horizon=record['horizon'],max_states=12000)
        assert compiled.fingerprint==record['selection']['fingerprint']
        case=TransferInstance(record['game'],'public_local',compiled.models,compiled.domain.goal(),
                              compiled.belief,compiled.horizon,compiled.domain.allowed)
        location,control,reason=projections(case)
        results={mode:measure(case,mode) for mode in ('capacity_lp','location_lp','control_lp')}
        assert len({r['optimum'] for r in results.values()})==1
        bounds={label:ControlCapacity(case.models,case.goal,case.allowed,indices)
                for label,indices in (('resource_only',()),('location',location),('location_stage',control))}
        rows.append(dict(game=case.name,public_prefix_length=record['next_step'],
            fingerprint=compiled.fingerprint,grounding_fingerprint_verified=True,
            horizon=case.horizon,projection_reason=reason,
            measurements=results,
            raw_capacity_bounds={label:printable(bound.lower(case.belief,case.horizon))
                                 for label,bound in bounds.items()},
            root_improved=results['control_lp']['root_lower']!=results['capacity_lp']['root_lower']))
    result=dict(api_calls=0,game_actions=0,game_baseline_reruns=0,
        source_sha256=sha256(source.read_bytes()).hexdigest(),cases=rows,
        protocol='Read-only existing finite local models, same fingerprints and strong all-model '
                 'success obligation. One diagnostic timing per mode, not a performance benchmark. '
                 'Every finite returned policy replayed. No new game checkpoints or hidden state.',
        limitation='Strong infeasibility differs from earlier preserve_opportunity semantics; '
                   'this is not an assessment of whether the full game quest is solvable.')
    destination=Path(__file__).parent/'results/2026-10-16-control-capacity/game_audit.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([dict(game=r['game'],raw=r['raw_capacity_bounds'],root_improved=r['root_improved'])
                      for r in rows]),flush=True)


if __name__ == '__main__':
    main()
