from itertools import combinations
from math import inf
import pytest
from scar_public.compiled_task import CompiledTask
from scar_public.certificate_refinement import RefinementCoverage, projection_view
from scar_public.incremental_channels import IncrementalCoverage, ChannelPool
from scar_public.multistep_refinement import MultistepCoverage, MultistepPlanner, scalar_path, path_core
from scar_public.work_scheduled_refinement import WorkCoverage, WorkLedger, WorkScheduledPlanner
from scar_public.cached_multistep_refinement import CachedMultistepCoverage, CachedMultistepPlanner, BatchedWorkPlanner
from scar_public.persistent_multistep_refinement import PersistentMultistepCoverage, FinalWorkPlanner
from scar_public.budgeted_planner import InferenceStop
from scar_public.test_symbolic_coverage import DOMAIN, PROBLEM, case
from scar_public.information_reference import independent_oracle, reachable_contexts


STAGED = '''(define (domain stages) (:predicates (hidden) (raw) (alternate) (stage) (done))
(:action mine :parameters () :effect (raw))
(:action alternate :parameters () :effect (alternate))
(:action prepare :parameters () :precondition (or (raw) (alternate)) :effect (stage))
(:action finish :parameters () :precondition (stage) :effect (done))
(:action sense :parameters () :observe (hidden)))'''
START = '''(define (problem stages) (:domain stages)
(:init (oneof (hidden) (not (hidden)))) (:goal (done)))'''


def test_multistep_core_needs_all_links_and_preserves_real_progress():
    t = CompiledTask(STAGED, START, projection_predicates=('stage', 'done'))
    one = RefinementCoverage(t)
    assert one.select(list(t.belief))[0] == 0
    b = MultistepCoverage(t); b.query_budget = 2
    extra, _ = b.select(list(t.belief))
    assert {t.atom_names[i] for i in range(len(t.atom_names)) if extra & (1 << i)} == {('raw',), ('alternate',)}
    assert b.multistep_stats['multi_step_paths'] > 0
    # Keeping only either member of the sufficient core does NOT exclude the
    # same path. Retaining both does; a hitting-set interpretation is wrong.
    for i in range(len(t.atom_names)):
        if extra & (1 << i):
            c = IncrementalCoverage(projection_view(t, 1 << i))
            assert c.capacity(c.project(next(iter(t.belief))[1]), 2) == 2
    c = IncrementalCoverage(projection_view(t, extra))
    key = c.project(next(iter(t.belief))[1])
    assert c.capacity(key, 2) == 0
    assert c.capacity(key, 3) == 2  # Dynamic effects must not be frozen.
    p = MultistepPlanner(t); ans = p.solve(t.belief, 3)
    assert ans.upper == p.verify(t.belief, 3, ans.policy) == 3


def test_work_budget_charges_misses_resumes_and_leaves_hits_free():
    t = CompiledTask(DOMAIN, PROBLEM, projection_predicates=('flag','done'))
    pool = ChannelPool(t); pool.work_ledger = ledger = WorkLedger()
    b = WorkCoverage(t, pool=pool)
    key = b.project(next(iter(t.belief))[1]); mask = (1 << len(t.models))-1
    ledger.earned = ledger.query_remaining = 2
    with pytest.raises(InferenceStop):
        b.relational_capacity(key, mask, 3)
    assert (b.canonical(key,3),mask,3) not in b.relation_cache
    ledger.earned = ledger.query_remaining = 100000
    value = b.relational_capacity(key, mask, 3)
    expected = IncrementalCoverage(t).relational_capacity(key, mask, 3)
    assert value == expected
    used = ledger.used
    ledger.earned = used; ledger.query_remaining = 0
    assert b.relational_capacity(key, mask, 3) == expected
    assert ledger.used == used


def test_intermediate_delete_cannot_spontaneously_reappear():
    domain = '''(define (domain stages) (:predicates (hidden) (raw) (stage) (done))
    (:action prepare :parameters () :effect (and (stage) (not (raw))))
    (:action finish :parameters () :precondition (and (stage) (raw)) :effect (done))
    (:action replenish :parameters () :effect (raw))
    (:action sense :parameters () :observe (hidden)))'''
    problem = START.replace('(:init ', '(:init (raw) ')
    t = CompiledTask(domain, problem, projection_predicates=('stage','done'))
    b = MultistepCoverage(t); b.query_budget = 2
    assert RefinementCoverage(t).select(list(t.belief))[0] == 0
    extra, _ = b.select(list(t.belief))
    raw = t.atom_names.index(('raw',))
    assert extra == 1 << raw
    assert b.multistep_stats['traces'][0]['actions'] == ['prepare','finish']
    c = IncrementalCoverage(projection_view(t,extra)); key = c.project(next(iter(t.belief))[1])
    assert c.capacity(key,2) == 0
    assert c.capacity(key,3) == 2


def test_cached_harvest_excludes_the_same_temporal_witness():
    t=CompiledTask(STAGED,START,projection_predicates=('stage','done'))
    c=CachedMultistepCoverage(t)
    prune,e=c.decide(t.belief,2)
    assert prune and e['reason']=='scalar_prune'
    assert c.multistep_stats['refinements']==1
    assert c.multistep_stats['multi_step_paths']>=1
    assert not c.decide(t.belief,3)[0]


def test_admission_skips_do_not_consume_attempts_or_disable_recursive_search():
    t=CompiledTask(DOMAIN,PROBLEM)
    p=BatchedWorkPlanner(t);p.next_batch=20000
    answer=p.solve(t.belief,3)
    assert answer.exact and answer.upper==2
    assert p.verify(t.belief,3,answer.policy)==2
    assert p.target_attempts==0 and p.batch_stats['admission_skips']>0


def test_selected_identities_survive_temporary_common_value_loss():
    from scar_public.finite_planner import State
    t=CompiledTask(STAGED,START,projection_predicates=('stage','done'))
    b=PersistentMultistepCoverage(t)
    assert b.decide(t.belief,2)[0]
    chosen=b.retained_identities
    raw=1<<t.atom_names.index(('raw',))
    worlds=sorted(t.belief,key=lambda w:w[0]);name,s=worlds[0]
    # A valid-looking diagnostic belief with one formerly common fact different.
    mixed=frozenset([(name,State((s.symbols[0]|raw,True),s.resources))]+worlds[1:])
    b.decide(mixed,1)
    assert b.retained_identities==chosen and not b.active_extra&raw
    assert b.decide(t.belief,2)[0]
    assert b.active_extra==chosen and b.persistence_stats['restored']>0


def validate():
    checks = prunes = replays = 0
    for projection in ((), ('flag',), ('done','flag')):
        for resources, costs in [((),None), ((1,0),{'make':(1,0),'sense':(0,1),'flag':(1,0)}),
                                  ((3,1),{'make':(1,0),'sense':(0,1),'flag':(1,0)})]:
            t = CompiledTask(DOMAIN, PROBLEM, projection_predicates=projection,
                resources=resources, resource_costs=costs)
            oracle = independent_oracle(case(t))
            bound = MultistepCoverage(t)
            planners = [MultistepPlanner(t), WorkScheduledPlanner(t), WorkScheduledPlanner(t,False),
                CachedMultistepPlanner(t),BatchedWorkPlanner(t),BatchedWorkPlanner(t,False),
                FinalWorkPlanner(t),FinalWorkPlanner(t,False)]
            for belief, h in reachable_contexts(case(t)):
                for size in range(1,len(belief)+1):
                    for ws in combinations(belief,size):
                        sub = frozenset(ws)
                        if any(not t.allowed(s) for _,s in sub):
                            continue
                        truth = oracle(sub,h)
                        prune,_ = bound.decide(sub,h)
                        assert not prune or truth == inf
                        prunes += prune
                        for planner in planners:
                            answer = planner.solve(sub,h)
                            assert answer.exact and answer.upper == truth
                            if truth < inf:
                                assert planner.verify(sub,h,answer.policy) == truth
                                replays += 1
                        checks += 1
    return dict(contexts=checks, certified_rejections=prunes, policy_replays=replays)


def test_all_completed_rejections_and_plans_against_independent_oracle():
    assert validate()['contexts'] > 100
