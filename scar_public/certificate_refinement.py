"""Bound-only, counterexample-guided retention of known progress atoms.

Minimum means minimum cardinality for the collected concrete saturation witnesses,
within a three-atom cap. It does NOT mean a globally optimal abstraction. Selection
never proves infeasibility: only a completed conservative capacity calculation does.
"""
from copy import copy
from time import perf_counter
from scar_public.direct_saturation import SaturationCoverage
from scar_public.decision_coverage import DecisionCoverage, DecisionPlanner
from scar_public.finite_planner import State
from scar_public.symbolic_task import atoms
from scar_public.budgeted_planner import InferenceStop


def indices(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def minimum_hitting_set(clauses, limit=3, check=lambda: None, node_limit=4096):
    """Exact minimum up to limit; None means proved no solution within the cap.

    Work interruption raises InferenceStop, never returns a partial optimum.
    """
    clauses = tuple(sorted(set(clauses), key=lambda x: (x.bit_count(), x)))
    if any(c == 0 for c in clauses):
        return None
    work = 0
    for size in range(limit+1):
        def visit(chosen):
            nonlocal work
            check(); work += 1
            if work > node_limit:
                raise InferenceStop()
            pending = [c for c in clauses if not c & chosen]
            if not pending:
                return chosen
            if chosen.bit_count() == size:
                return None
            # A solution must intersect every pending clause. Enumerating one
            # entire clause is complete; order only breaks equal-size ties.
            for i in indices(pending[0]):
                answer = visit(chosen | (1 << i))
                if answer is not None:
                    return answer
            return None
        answer = visit(0)
        if answer is not None:
            return answer
    return None


def projection_view(task, extra):
    result = copy(task)
    result.projection = tuple(sorted(set(task.projection) | set(indices(extra))))
    result.projection_mask = task.projection_mask | extra
    return result


class RefinementCoverage(SaturationCoverage):
    def __init__(self, task, selection='certificate'):
        super().__init__(task)
        self.selection = selection
        self.refined = {}
        self.selection_cache = {}
        self.refinement_stats = dict(queries=0, certificates=0, witness_tests=0,
            selection_cache_hits=0, selected=0, added_atoms=0, cap_exceeded=0,
            no_known_separator=0, round_limit=0, constructed_certificate_removed=0,
            refined_queries=0, refined_scalar_prunes=0, refined_relation_prunes=0,
            refined_passes=0, selection_seconds=0., inference_seconds=0.,
            witness_seconds=0., refinement_cache_limit=0)
        self.goal_atoms = set(atoms(task.goal_expr))

    def known(self, live):
        first = live[0][1].symbols[0]
        differing = 0
        for _, state in live:
            differing |= first ^ state.symbols[0]
        common = self.task.dynamic_mask & ~differing & ~self.task.projection_mask
        return first, common

    def certificate(self, live, extra, first, common):
        """One common-action certificate and its disjunctive separator clause.

        Each member records an executable, possibly unreachable abstract prestate.
        A known atom differing in ANY member invalidates that specific certificate.
        """
        resources = live[0][1].resources
        mask = sum(self.model_bits[n] for n, _ in live)
        statics = [s for s, group in self.group_masks.items() if group & mask]
        fixed_mask = self.fixed_mask | extra
        projected = first & (self.task.projection_mask | extra)
        local = 0
        for name, assignments in self.achievers.items():
            self.check()
            a = self.task.actions[name]
            if any(r < c for r, c in zip(resources, a.consumption)):
                continue
            witnesses = []
            clause = 0
            for static in statics:
                fixed = static | projected
                for pos, neg in assignments:
                    if pos & fixed_mask & ~fixed or neg & fixed_mask & fixed:
                        continue
                    local += 1; self.refinement_stats['witness_tests'] += 1
                    if local > 2048 or self.refinement_stats['witness_tests'] > 50000:
                        raise InferenceStop()
                    bits = fixed | (pos & ~fixed_mask)
                    state = State((bits, True), resources)
                    child, _ = self.task.step(state, name)
                    if (self.task.allowed(child) and not self.task.goal.holds(state)
                            and self.task.goal.holds(child)):
                        witnesses.append((static, bits))
                        clause |= (bits ^ first) & common
                        break
                else:
                    break
            else:
                self.refinement_stats['certificates'] += 1
                return dict(action=name, witnesses=witnesses, clause=clause)
        return None

    def select(self, live):
        first, common = self.known(live)
        # Exact belief-specific selection; masks are never transferred across
        # beliefs with different known values, resources, or surviving identities.
        memo = frozenset(live)
        if memo in self.selection_cache:
            self.refinement_stats['selection_cache_hits'] += 1
            return self.selection_cache[memo]
        extra = 0; clauses = []; actions = []
        for _ in range(32):
            certificate = self.certificate(live, extra, first, common)
            if certificate is None:
                if clauses:
                    self.refinement_stats['constructed_certificate_removed'] += 1
                result = extra, dict(clauses=len(clauses), actions=actions,
                    constructed_certificate_removed=bool(clauses), minimal_for_collected=True)
                break
            clauses.append(certificate['clause']); actions.append(certificate['action'])
            if not certificate['clause']:
                self.refinement_stats['no_known_separator'] += 1
                result = 0, dict(reason='no_known_separator', clauses=len(clauses))
                break
            extra = minimum_hitting_set(clauses, check=self.check)
            if extra is None:
                self.refinement_stats['cap_exceeded'] += 1
                result = 0, dict(reason='three_atom_cap', clauses=len(clauses))
                break
        else:
            self.refinement_stats['round_limit'] += 1
            result = 0, dict(reason='certificate_round_limit', clauses=len(clauses))
        if len(self.selection_cache) < 4096:
            self.selection_cache[memo] = result
        return result

    def decide(self, belief, budget, mode='relation_gate'):
        self.refinement_stats['queries'] += 1
        live = [(n, s) for n, s in belief if not self.task.goal.holds(s)]
        if budget < 1 or len(live) < 2 or len({self.project(s) for _, s in live}) != 1:
            return False, dict(reason='refinement_inapplicable')
        started = perf_counter()
        try:
            extra, evidence = self.select(live)
        finally:
            self.refinement_stats['selection_seconds'] += perf_counter()-started
        if not extra:
            # Keep the previous implementation and its proven skip when there
            # was no obstructing certificate, or the refinement budget ran out.
            prune, old = super().decide(belief, budget, mode)
            return prune, dict(old, refinement=evidence)
        if self.selection == 'goal_first':
            _, common = self.known(live)
            ranked = sorted(indices(common), key=lambda i: (i not in self.goal_atoms, i))
            extra = sum(1 << i for i in ranked[:extra.bit_count()])
        self.refinement_stats['selected'] += 1
        self.refinement_stats['added_atoms'] += extra.bit_count()
        evidence = dict(evidence, selection=self.selection,
            added_atoms=[self.task.atom_names[i] for i in indices(extra)],
            known_values=[bool(live[0][1].symbols[0] & (1 << i)) for i in indices(extra)])
        if extra not in self.refined:
            if len(self.refined) >= 16:
                self.refinement_stats['refinement_cache_limit'] += 1
                return False, dict(reason='refinement_cache_limit', refinement=evidence)
            self.check()
            self.refined[extra] = DecisionCoverage(projection_view(self.task, extra))
        refined = self.refined[extra]
        refined.deadline = self.deadline
        self.refinement_stats['refined_queries'] += 1
        started = perf_counter()
        try:
            prune, answer = refined.decide(belief, budget, 'relation_threshold')
        finally:
            self.refinement_stats['inference_seconds'] += perf_counter()-started
        if prune:
            self.refinement_stats['refined_'+('scalar' if answer['reason']=='scalar_prune' else 'relation')+'_prunes'] += 1
        else:
            self.refinement_stats['refined_passes'] += 1
        return prune, dict(answer, reason='refined_'+answer['reason'], refinement=evidence)

    @property
    def stats(self):
        return dict(super().stats, refinement=dict(self.refinement_stats,
            projections=len(self.refined), children=[b.stats for b in self.refined.values()]))


class RefinementPlanner(DecisionPlanner):
    # Do not override MODES: superclass validates its own construction mode.
    def __init__(self, task, mode='refine_certificate'):
        if mode not in ('refine_certificate', 'refine_goal_first'):
            raise ValueError(mode)
        super().__init__(task, 'relation_gate')
        self.target_coverage = RefinementCoverage(task,
            'goal_first' if mode == 'refine_goal_first' else 'certificate')
