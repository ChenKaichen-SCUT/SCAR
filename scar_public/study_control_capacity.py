"""Frozen-instance comparison of resource, location and stage coverage bounds."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from statistics import median
from time import perf_counter

from scar_public.control_capacity import ControlInformationPlanner
from scar_public.finite_planner import printable
from scar_public.information_bound import InformationBoundPlanner
from scar_public.information_instances import study_grid, workshop
from scar_public.information_reference import independent_oracle
from scar_public.information_transfer import production_grid, bridge_grid
from scar_public.study_information_bound import measure as original_measure, numeric


MODES=InformationBoundPlanner.MODES+('location_lp','location_single','control_lp','control_single')


def projections(case):
    if case.family == 'delayed_observation':
        return (), (0,), 'Known scan progress; there is no location variable.'
    if case.family.startswith('recipe_') or case.family == 'public_local':
        return (0,), (0,)+tuple(range(2,len(case.models[0].domains))), \
            'Location and observed craft-event flags; elapsed-action counter deliberately omitted.'
    return (0,), (0,), 'Location; intermediate-product and fuel stages already occur in the resource vector.'


def measure(case,mode):
    if mode in InformationBoundPlanner.MODES:
        return original_measure(case,mode)
    location,control,_=projections(case)
    indices=location if mode.startswith('location_') else control
    started=perf_counter()
    planner=ControlInformationPlanner(case.models,case.goal,case.allowed,
                                      base=mode.rsplit('_',1)[1],symbol_indices=indices)
    constructed=perf_counter()
    root=planner.initial(case.belief,case.horizon).lower
    bounded=perf_counter()
    root_stats=planner.statistics()
    answer=planner.solve(case.belief,case.horizon)
    finished=perf_counter()
    assert answer.exact
    if isfinite(answer.upper):
        assert planner.verify(case.belief,case.horizon,answer.policy) == answer.upper
    return dict(mode=mode,root_lower=printable(root),optimum=printable(answer.upper),
                seconds=finished-started,construct_seconds=constructed-started,
                root_bound_seconds=bounded-constructed,search_seconds=finished-bounded,
                root_statistics=root_stats,statistics=planner.statistics())


def aliases_for(case):
    location,control,_=projections(case)
    aliases={}
    if location == control:
        aliases.update((f'location_{base}',f'control_{base}') for base in ('lp','single'))
    if not location:
        aliases.update((f'location_{base}',f'capacity_{base}') for base in ('lp','single'))
    return aliases


def stage_grid():
    for case in study_grid():
        if case.family == 'delayed_observation':
            yield case


def summary(rows):
    return {mode:dict(instances=len(rows),
        total_seconds=sum(r['measurements'][mode]['median_seconds'] for r in rows),
        end_to_end_seconds=sum(r['compile_seconds']+r['measurements'][mode]['median_seconds'] for r in rows),
        search_expanded=sum(r['measurements'][mode]['statistics']['search_expanded'] for r in rows),
        bound_dp_nodes=sum(r['measurements'][mode]['statistics']['single_nodes']+
                           r['measurements'][mode]['statistics']['pair_nodes'] for r in rows),
        capacity_dp_nodes=sum((r['measurements'][mode]['statistics']['coverage'] or {}).get('dp_nodes',0) for r in rows),
        compiled_transitions=sum((r['measurements'][mode]['statistics']['coverage'] or {}).get('compiled_transitions',0) for r in rows),
        root_exact=sum(r['measurements'][mode]['root_lower']==r['optimum'] for r in rows),
        root_stricter_than_old_capacity=sum(numeric(r['measurements'][mode]['root_lower'])>
            numeric(r['measurements']['capacity_lp' if mode.endswith('lp') else 'capacity_single']['root_lower']) for r in rows))
        for mode in MODES}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repetitions',type=int,default=3)
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'results/2026-10-16-control-capacity/analysis.json')
    args=parser.parse_args()
    assert args.repetitions > 0
    source=Path(__file__).parent
    prior_paths=('results/2026-10-16-information-transfer/analysis.json',
                 'results/2026-10-16-information-bound/analysis.json')
    prior={}
    for name in prior_paths:
        saved=json.loads((source/name).read_text(encoding='utf-8'))
        prior.update((r['name'],r) for r in saved['cases'])
    original_measure(workshop(scan_steps=1,horizon=2),'lp')
    rows=[];started=perf_counter()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for generator in (production_grid,bridge_grid,stage_grid):
        iterator=iter(generator())
        while True:
            t=perf_counter()
            try:
                case=next(iterator)
            except StopIteration:
                break
            compile_seconds=perf_counter()-t
            saved=prior[case.name]
            assert json.loads(json.dumps(case.metadata)) == saved['config'],case.name
            oracle=independent_oracle(case)
            truth=oracle(case.belief,case.horizon)
            assert printable(truth) == saved['optimum']
            aliases=aliases_for(case)
            modes=[m for m in MODES if m not in aliases]
            samples=defaultdict(list)
            for repeat in range(args.repetitions):
                offset=(len(rows)+repeat)%len(modes)
                for mode in modes[offset:]+modes[:offset]:
                    run=measure(case,mode)
                    assert numeric(run['root_lower']) <= truth
                    assert numeric(run['optimum']) == truth
                    if mode in InformationBoundPlanner.MODES:
                        old=saved['measurements'][mode]
                        assert run['root_lower']==old['root_lower']
                        assert run['statistics']==old['statistics'],(case.name,mode,'baseline work changed')
                    samples[mode].append(run)
            measurements={}
            for mode,runs in samples.items():
                assert all(r['statistics']==runs[0]['statistics'] for r in runs)
                measurements[mode]=dict(runs[0],median_seconds=median(r['seconds'] for r in runs),
                    timing_samples_seconds=[r['seconds'] for r in runs],
                    construct_samples_seconds=[r['construct_seconds'] for r in runs],
                    bound_samples_seconds=[r['root_bound_seconds'] for r in runs],
                    search_samples_seconds=[r['search_seconds'] for r in runs])
            for mode,alias in aliases.items():
                measurements[mode]=dict(measurements[alias],mode=mode,alias_of=alias)
            for base in ('lp','single'):
                old,loc,new=[numeric(measurements[f'{prefix}_{base}']['root_lower'])
                             for prefix in ('capacity','location','control')]
                assert old <= loc <= new <= truth,(case.name,base,old,loc,new,truth)
            location,control,explanation=projections(case)
            rows.append(dict(name=case.name,family=case.family,config=case.metadata,
                cohort='stage_diagnostic' if case.family=='delayed_observation' else 'frozen_transfer_36',
                location_indices=location,control_indices=control,projection_reason=explanation,
                optimum=printable(truth),compile_seconds=compile_seconds,
                oracle_subproblems=oracle.cache_info().currsize,measurements=measurements,
                frozen_baseline_values_and_work_verified=True))
            oracle.cache_clear()
            args.output.with_suffix('.partial.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
            print(json.dumps(dict(completed=len(rows),name=case.name,optimum=printable(truth),
                old=measurements['capacity_lp']['root_lower'],new=measurements['control_lp']['root_lower'],
                old_seconds=measurements['capacity_lp']['median_seconds'],
                new_seconds=measurements['control_lp']['median_seconds'])),flush=True)
    result=dict(date='2026-10-16',api_calls=0,game_actions=0,timing_repetitions=args.repetitions,
        protocol='Fresh planner caches, rotated method order; construction, bounds and search timed. '
                 'Common model compilation separately reported and included in end_to_end_seconds. '
                 'Oracle and policy replay excluded equally. Aliases reuse identical computation explicitly. '
                 'Local offline baselines re-timed; no LLM/game baselines rerun.',
        scope='36 unchanged transfer instances, plus the 24 pre-existing delayed-stage diagnostics. '
              'Not new games or workflows; selection was based on prior documented failure mechanisms.',
        prior_sha256={p:sha256((source/p).read_bytes()).hexdigest() for p in prior_paths},
        source_sha256={n:sha256((source/n).read_bytes()).hexdigest() for n in (
            'control_capacity.py','study_control_capacity.py','information_transfer.py','information_instances.py',
            'finite_planner.py','information_bound.py','observation_capacity.py','resource_competition.py')},
        summary=summary(rows),
        cohorts={c:summary([r for r in rows if r['cohort']==c]) for c in sorted({r['cohort'] for r in rows})},
        families={f:summary([r for r in rows if r['family']==f]) for f in sorted({r['family'] for r in rows})},
        cases=rows,wall_seconds=perf_counter()-started)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(completed=len(rows),wall_seconds=result['wall_seconds'])),flush=True)


if __name__ == '__main__':
    main()
