"""Guarded elimination of raw, JOINT action-semantic profiles across local trials.

Guards are explicit applicability assumptions, not a proof of stationarity. The
current adapter supports one recipe. An ID such as m0 is compilation-local; only
its complete parameter aliases may survive recompilation. Search failure is
never evidence about the environment. No evidence changes the LLM prompt here.
"""
from itertools import product

from scar_public.causal_model import digest
from scar_public.resource_competition import ResourceGap


def evidence_context(problem):
    if len(problem.recipes) != 1:
        raise ResourceGap('persistent evidence requires one recipe; joint recipe correlations unsupported')
    recipe = problem.recipes[0]
    source = problem.source or {}
    guard = dict(semantics='resource-competition-v1', output=recipe.output,
        needs=sorted(recipe.needs), stations=sorted(recipe.stations),
        locations=sorted(problem.locations), routes=problem.routes, location=problem.start_location,
        items=sorted(problem.items), bag_name=problem.bag_name,
        hand_capacity=problem.hand_capacity, bag_capacity=problem.bag_capacity,
        hand_background=problem.hand_background, bag_background=problem.bag_background,
        equipment=source.get('equipment'), recipe_evidence=source.get('recipe'),
        station_evidence=source.get('station'), assumptions=sorted(problem.assumptions),
        universe=sorted(product(recipe.quantity_modes,recipe.access_modes)))
    # Counts, elapsed public history, and offered craft batch sizes vary between
    # queries. All other semantics above must match. Time-dependent bonuses are
    # NOT covered: within-guard stationarity remains an unestablished assumption.
    return digest(guard), guard


class EvidenceBank:
    def __init__(self, state=None):
        self.state = state if state is not None else dict(version=1, revision=0, contexts={}, audit=[])
        if self.state.get('version') != 1: raise ResourceGap('unsupported evidence ledger version')

    def entry(self, problem):
        key,guard = evidence_context(problem)
        if key not in self.state['contexts']:
            self.state['contexts'][key] = dict(guard=guard, epoch=0, allowed=guard['universe'], observations=0)
        return key,self.state['contexts'][key]

    def query(self, problem):
        key,entry = self.entry(problem)
        allowed = entry['allowed']; universe = entry['guard']['universe']
        used = set(map(tuple,allowed)) != set(map(tuple,universe))
        metadata = dict(context=key, epoch=entry['epoch'], reused=used,
            raw_profiles_before=len(universe), raw_profiles_after=len(allowed),
            supporting_observations=entry['observations'],
            stationarity='assumed within guard; hidden modifiers are not ruled out')
        return ({problem.recipes[0].output:allowed} if used else None),metadata

    def invalidate(self, problem, reason):
        key,entry = self.entry(problem)
        old_epoch = entry['epoch']
        entry.update(epoch=old_epoch+1, allowed=entry['guard']['universe'], observations=0)
        self.state['revision'] += 1
        event = dict(kind='REVOKED',context=key,epoch=old_epoch,reason=reason)
        self.state['audit'].append(event)
        return event

    def observe(self, compiled, event, expected_epoch):
        problem = compiled.domain.problem
        key,entry = self.entry(problem)
        if entry['epoch'] != expected_epoch:
            raise ResourceGap('evidence epoch changed during an active trial')
        if event.get('status') in ('MODEL_MISMATCH','OBSERVATION_GAP'):
            return self.invalidate(problem,event['status'])
        # Only an actual matched transition may eliminate a profile. Infeasible
        # or UNKNOWN search results, and the planner's exemptions, never enter.
        if event.get('status') != 'ACTIVE' or 'observed' not in event or not event.get('surviving_models'):
            raise ResourceGap('evidence requires a matched public transition')
        output = problem.recipes[0].output
        survivors = set(event['surviving_models'])
        if not survivors <= set(compiled.aliases): raise ResourceGap('unknown compilation-local model ID')
        compatible = {tuple(p) for m in survivors for p in compiled.aliases[m][output]}
        before = set(map(tuple,entry['allowed'])); after = before & compatible
        if not after: return self.invalidate(problem,'inconsistent evidence intersection')
        entry['allowed'] = sorted(after); entry['observations'] += 1
        self.state['revision'] += int(after != before)
        record = dict(kind='MATCHED_TRANSITION',context=key,epoch=entry['epoch'],
            action=event['action'],observation_sha256=event['observation_sha256'],
            fingerprint=compiled.fingerprint,before=len(before),after=len(after),
            eliminated=sorted(before-after))
        self.state['audit'].append(record)
        return record
