"""Refine existential multi-step paths by restoring omitted state links.

A path is a witness of the optimistic scalar tree, NOT a real policy. An UNSAT
core contains a *set* of atom links sufficient to rule out this path. All atoms
in that core must be retained; hitting one core atom is not sufficient. Only a
completed conservative capacity calculation may prune the exact search.
"""
from time import perf_counter
import z3
from scar_public.amortized_refinement import AmortizedCoverage
from scar_public.certificate_refinement import indices, projection_view
from scar_public.incremental_channels import IncrementalCoverage
from scar_public.decision_coverage import DecisionPlanner
from scar_public.demand_coverage import formula, negate, junction
from scar_public.symbolic_coverage import Unavailable
from scar_public.budgeted_planner import InferenceStop


def scalar_path(bound, key, bit, depth, memo=None):
    """One named candidate's path in the already computed maximizing C0 tree."""
    bound.check()
    if depth == 0:
        return None
    if memo is None:
        memo = {}
    key = bound.canonical(key, depth)
    cache_key = key, bit, depth
    if cache_key in memo:
        return memo[cache_key]
    bound.capacity(key, depth)
    chosen = bound.scalar_witness.get((key, depth))
    if chosen is None:
        return None
    name, goals, children = bound.mask_channels[key][chosen]
    if goals & bit:
        answer = [(key, name, None, None)]
    else:
        answer = None
        for eligible, nxt in children:
            if not eligible & bit:
                continue
            tail = scalar_path(bound, nxt, bit, depth-1, memo)
            if tail is not None:
                # Recover the actual observation label omitted by capacity's
                # count representation; projected states alone are insufficient.
                _, core = bound.channel_pool.action_channels(bound, key[1], bound.task.actions[name])
                obs = next(o for o, p, m in core if p == nxt[1] and m & bit)
                answer = [(key, name, nxt, obs)] + tail
                break
    memo[cache_key] = answer
    return answer


def path_core(bound, path, initial_bits, eligible, stats):
    """Return sufficient additional links, or zero for a realizable path.

    Each step has an independent pre-state. Assumption L_i restores both the
    actual initial value and EVERY adjacent transition link for omitted atom i.
    Existing projection/static constraints are unconditional. UNSAT is checked
    under eligible links only, so the returned core is implementable by our
    common-root-key projection. SAT need not mean a real path for unlinked atoms.
    """
    task = bound.task
    solver = z3.Solver()
    before_rows, after_rows = [], []
    static = initial_bits & ~task.dynamic_mask
    for t, (key, name, nxt, obs) in enumerate(path):
        bound.check()
        variables = [z3.Bool('trace_%d_%d' % (t, i)) for i in range(len(task.atom_names))]
        def before(i):
            if i not in task.dynamic:
                return bool(static & (1 << i))
            if task.projection_mask & (1 << i):
                return bool(key[1] & (1 << i))
            return variables[i]
        a = task.actions[name]
        adds, deletes = bound.channel_pool.effects[name]
        post = {}
        def after(i):
            if i not in post:
                add = junction((formula(g, before) for g in adds.get(i, ())), False)
                delete = junction((formula(g, before) for g in deletes.get(i, ())), False)
                post[i] = junction((add, junction((before(i), negate(delete)), True)), False)
            return post[i]
        solver.add(formula(a.pre, before), negate(formula(task.goal_expr, before)))
        if nxt is None:
            solver.add(formula(task.goal_expr, after))
        else:
            solver.add(negate(formula(task.goal_expr, after)))
            for i in task.projection:
                solver.add(after(i) == bool(nxt[1] & (1 << i)))
            if a.observation is not None:
                solver.add(formula(a.observation, after) == obs[0])
        before_rows.append({i: before(i) for i in indices(eligible)})
        after_rows.append({i: after(i) for i in indices(eligible)})
    labels = {}
    for i in indices(eligible):
        label = z3.Bool('link_%d' % i)
        links = [before_rows[0][i] == bool(initial_bits & (1 << i))]
        links += [before_rows[t][i] == after_rows[t-1][i] for t in range(1, len(path))]
        solver.add(z3.Implies(label, z3.And(*links)))
        labels[label.decl().name()] = i
    def check(assumptions):
        bound.check()
        remaining = bound.deadline - perf_counter()
        solver.set(timeout=max(1, min(1000, int(remaining*1000))) if remaining != float('inf') else 1000)
        stats['sat_checks'] += 1
        answer = solver.check(*assumptions)
        if answer == z3.unknown:
            raise Unavailable('multi-step trace SAT unknown')
        return answer
    # The independent-step path must be satisfiable. A failure is an extraction
    # bug, not evidence about the planning problem.
    if check([]) != z3.sat:
        raise AssertionError('inconsistent extracted abstract path')
    assumptions = [z3.Bool(n) for n in labels]
    if check(assumptions) == z3.sat:
        stats['linked_satisfiable'] += 1
        return 0
    core = list(solver.unsat_core())
    # Deletion-minimal core, not minimum-cardinality projection. Keep the last
    # sufficient core if the optional minimization budget expires.
    for label in tuple(core):
        if stats['core_minimizations'] >= 64:
            break
        trial = [v for v in core if v.decl().name() != label.decl().name()]
        stats['core_minimizations'] += 1
        if check(trial) == z3.unsat:
            core = trial
    result = sum(1 << labels[v.decl().name()] for v in core)
    assert result
    stats['spurious_paths'] += 1
    return result


class MultistepCoverage(AmortizedCoverage):
    def __init__(self, task, **kwargs):
        super().__init__(task, **kwargs)
        self.query_budget = 0
        self.multistep_stats = dict(paths=0, multi_step_paths=0, spurious_paths=0,
            linked_satisfiable=0, sat_checks=0, core_minimizations=0, refinements=0,
            capped_cores=0, interrupted=0, seconds=0., traces=[])

    def select(self, live):
        extra, evidence = super().select(live)
        first, common = self.known(live)
        start = perf_counter()
        selection_deadline = min(self.deadline, start + .10)
        n = len(live)
        try:
            for _ in range(3):
                bound = self.refined.get(extra)
                if bound is None:
                    bound = self.coverage_type(projection_view(self.task, extra), pool=self.channel_pool)
                    self.refined[extra] = bound
                bound.deadline = selection_deadline
                key = bound.project(live[0][1])
                for depth in range(1, min(8, self.query_budget)+1):
                    if bound.capacity(key, depth) >= n:
                        break
                else:
                    break
                changed = False
                memo = {}
                for name, state in sorted(live, key=lambda w: w[0]):
                    path = scalar_path(bound, key, bound.model_bits[name], depth, memo)
                    if path is None:
                        continue
                    self.multistep_stats['paths'] += 1
                    self.multistep_stats['multi_step_paths'] += len(path) > 1
                    core = path_core(bound, path, state.symbols[0], common & ~extra, self.multistep_stats)
                    if not core:
                        continue
                    if (extra | core).bit_count() > 6:
                        self.multistep_stats['capped_cores'] += 1
                        continue
                    if len(self.multistep_stats['traces']) < 16:
                        self.multistep_stats['traces'].append(dict(model=name, depth=depth,
                            actions=[p[1] for p in path],
                            added_atoms=[self.task.atom_names[i] for i in indices(core)]))
                    extra |= core
                    self.multistep_stats['refinements'] += 1
                    changed = True
                    break
                if not changed:
                    break
        except (InferenceStop, Unavailable):
            # Completed earlier refinements remain sound choices. Nothing in
            # this selector, including UNSAT, is a task-infeasibility proof.
            self.multistep_stats['interrupted'] += 1
        finally:
            self.multistep_stats['seconds'] += perf_counter()-start
        return extra, dict(evidence, multistep=True)

    def decide(self, belief, budget, mode='relation_gate'):
        self.query_budget = budget
        return super().decide(belief, budget, mode)

    @property
    def stats(self):
        return dict(super().stats, multistep=dict(self.multistep_stats))


class MultistepPlanner(DecisionPlanner):
    def __init__(self, task):
        super().__init__(task, 'relation_threshold')
        self.target_coverage = MultistepCoverage(task)
