"""Finite differential checks, including erased identity and late goal loss."""
from collections import deque
from itertools import combinations
from math import inf
from scar_public.symbolic_task import SymbolicTask, ev
from scar_public.compiled_task import CompiledTask
from scar_public.reachable_labels import LabelClosure, ReachableCoverage, ReachablePlanner
from scar_public.bounded_resource_coverage import BoundedResourceCoverage
from scar_public.budgeted_planner import BudgetedPlanner
from scar_public.information_reference import independent_oracle


def dynamic_identity(n=3, budget=2, consume_at_finish=False, ambiguous_ready=False):
    # Consuming a token makes the initial uncertain predicates dynamic. Labels
    # must remember where the surviving token could have originated. The stage
    # determines which token can disappear; no immutable identity tag is added.
    preds = ' '.join(f'(h{i}) (p{i})' for i in range(n))
    actions = []
    costs = {}
    for omit in range(n):
        first = (omit+1) % n
        early = '(done)' if consume_at_finish else f'(and (done) (not (h{first})))'
        guard = f'(and (h{first}) (ready))' if ambiguous_ready else f'(h{first})'
        actions.append(f'(:action prepare{omit} :parameters () :precondition (start) '
            f':effect (and (not (start)) (p{omit}) (when {guard} {early})))')
        effects = ' '.join(f'(when (h{i}) (done))' for i in range(n) if i != omit)
        if consume_at_finish:
            effects += ' '+' '.join(f'(not (h{i}))' for i in range(n))
        if ambiguous_ready:
            effects += ' (not (ready))'
        actions.append(f'(:action finish{omit} :parameters () :precondition (p{omit}) '
            f':effect (and (not (p{omit})) (end) {effects}))')
        costs[f'prepare{omit}'] = costs[f'finish{omit}'] = (1,)
    actions.append('(:action recover :parameters () :precondition (end) :effect (done))')
    costs['recover'] = (1,)
    d = '(define (domain dynamic_identity) (:predicates (start) (end) (done) (ready) '+preds+') '+' '.join(actions)+')'
    p = '(define (problem d) (:domain dynamic_identity) (:init (start) '+('(ready) ' if ambiguous_ready else '')+'(oneof '+ ' '.join(f'(h{i})' for i in range(n))+')) (:goal (done)))'
    return CompiledTask(d, p, resources=(budget,), resource_costs=costs,
        projection_predicates=('start', 'end')+tuple(f'p{i}' for i in range(n)))


def concrete_states(task):
    for name, initial in task.belief:
        seen = {initial}; queue = deque([initial])
        while queue:
            s = queue.popleft()
            yield name, s
            for a in task.actions:
                nxt, _ = task.step(s, a)
                if task.allowed(nxt) and nxt not in seen:
                    seen.add(nxt); queue.append(nxt)


def test_dynamic_labels_break_the_single_static_class_collapse():
    for n in (3, 4, 8):
        t = dynamic_identity(n)
        old = BoundedResourceCoverage(t, 'lineage', 100000)
        new = ReachableCoverage(t)
        q = new.project(next(iter(t.belief))[1]); mask = (1 << n)-1
        assert len(old.group_masks) == 1
        assert old.relational_capacity(q, mask, 2) == n
        assert new.capacity(q, 2) == n
        assert new.relational_capacity(q, mask, 2) == n-1
        assert new.labels.stats['patterns_completed'] > 0


def test_all_small_subsets_against_independent_exact_oracle():
    for budget in (1, 2, 3):
        t = dynamic_identity(3, budget)
        c = ReachableCoverage(t)
        oracle = independent_oracle(t)
        worlds = sorted(t.belief, key=lambda x: x[0])
        for size in range(1, 4):
            for subset in combinations(worlds, size):
                belief = frozenset(subset); q = c.project(subset[0][1])
                mask = sum(c.model_bits[n] for n, _ in subset)
                for h in range(1, 4):
                    value = oracle(belief, h)
                    if value < inf:
                        assert c.capacity(q, h) >= size
                        assert c.relational_capacity(q, mask, h) >= size


def test_every_concrete_state_is_in_its_label_envelope():
    t = dynamic_identity(4, 3)
    closure = LabelClosure(t, lambda: None); closure.prepare()
    assert not closure.stats['interrupted']
    for name, s in concrete_states(t):
        bit = 1 << int(name[1:])
        group = next(g for g in closure.groups(s.resources) if g[2] & bit)
        assert all(s.symbols[0] & sum(1 << i for i in pat) in allowed for pat, allowed in group[1])


def test_interrupted_closure_never_publishes_an_incomplete_pattern():
    t = dynamic_identity()
    c = LabelClosure(t, lambda: None, work_limit=1); c.prepare()
    assert c.stats['interrupted'] and not c.completed
    assert all(not restrictions for _, restrictions, _ in c.groups(t.resources))


def test_goal_states_are_expanded_and_add_wins():
    d = '''(define (domain d) (:predicates (h) (g) (p))
      (:action mark :parameters () :effect (g))
      (:action leave :parameters () :precondition (g) :effect (and (not (g)) (p)))
      (:action both :parameters () :precondition (p) :effect (and (not (h)) (h))))'''
    p = '(define (problem p) (:domain d) (:init (unknown (h))) (:goal (g)))'
    t = SymbolicTask(d, p, resources=(3,), resource_costs={a: (1,) for a in ('mark', 'leave', 'both')})
    closure = LabelClosure(t, lambda: None, patterns=[tuple(sorted(t.dynamic))]); closure.prepare()
    for name, s in concrete_states(t):
        group = next(g for g in closure.groups(s.resources) if g[2] & (1 << int(name[1:])))
        assert all(s.symbols[0] & sum(1 << i for i in pat) in allowed for pat, allowed in group[1])


def test_search_same_optimum_and_replayed_policies():
    for resources in (2, 3):
        t = dynamic_identity(3, resources)
        values = []
        for mode in ('reachable_count', 'reachable_relation'):
            p = ReachablePlanner(t, mode); result = p.solve(t.belief, 3)
            assert result.exact
            values.append(result.upper)
            if result.upper < inf:
                assert p.verify(t.belief, 3, result.policy) == result.upper
        assert values == ([inf, inf] if resources == 2 else [3, 3])
