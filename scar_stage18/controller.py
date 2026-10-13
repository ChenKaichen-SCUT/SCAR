"""Transactional Stage16 S1/P1/P3 with public-evidence reliability overlays."""
import copy
from scar_stage17.budget_adapter import Budget100Controller
from scar_stage16.controller import BaselineController
from scar_v3.state import parse_action
from .acquisition import bound_store
from .consequences import ConsequenceMemory, public_frame
from . import execution_context, arbitration


class Controller18(Budget100Controller):
    def __init__(self):
        super().__init__('S1_P1_P3')
        self.consequences = ConsequenceMemory()
        self.acquisitions18 = []
        self.probe_candidates18 = []
        self.audit18 = {}
        self.outcome18 = {}

    def legacy_copy(self):
        obj = Budget100Controller()
        for name in list(obj.__dict__):
            if name in self.__dict__:
                obj.__dict__[name] = copy.deepcopy(self.__dict__[name])
        return obj

    def _acquire(self, name, amount, protect, use_container=True):
        old = super()._acquire(name, amount, protect, use_container)
        action, log = bound_store(self, old, hint=amount, source='FIFO_acquire') if old else (None, None)
        if log:
            self.acquisitions18.append(log)
        return action

    def local_collect(self, item, amount=1):
        old = super().local_collect(item, amount)
        action, log = bound_store(self, old, ground_need=amount, source='P3_local_collect') if old else (None, None)
        if log:
            self.acquisitions18.append(log)
        return action

    def collection(self, item, all_visible=False):
        old = super().collection(item, all_visible)
        action, log = bound_store(self, old, source='inherited_alternative') if old else (None, None)
        if log:
            self.acquisitions18.append(log)
        return action

    def assess(self, action):
        return execution_context.assess(self, action)

    def _probe(self, action, reason, source):
        result = super()._probe(action, reason, source)
        if result:
            self.probe_candidates18.append(dict(action=result, pending=copy.deepcopy(self.pending_probe),
                exploration=copy.deepcopy(self.explore_pending)))
        return result

    def choose(self, obs, proposal):
        self.table.observe(obs)
        self.acquisitions18, self.probe_candidates18 = [], []
        context = execution_context.build(self)
        before = copy.deepcopy(self)
        original = self.legacy_copy()
        old_candidate = original.choose(obs, proposal)
        trial = copy.deepcopy(self)
        candidate = Budget100Controller.choose(trial, obs, proposal)
        # Also bound a raw LLM store or alternative that bypassed _acquire.
        protected_p3 = trial.audit16.get('selected_module') == 'finish' and any(
            r['bounded_action'] == candidate and r['source'] == 'P3_local_collect' for r in trial.acquisitions18)
        if not protected_p3:
            bounded, log = bound_store(trial, candidate, source='final_candidate')
            if log:
                trial.acquisitions18.append(log)
                candidate = bounded or 'wait'
        checks = {name: execution_context.assess(before, action, context) for name, action in
            [('llm', proposal), ('original_controller', old_candidate), ('bounded_controller', candidate)]}
        final, reason = arbitration.choose(before, proposal, candidate, checks)
        # A restored proposal must obey acquisition constraints too; preserve
        # original text in the audit so a bounded proposal is never misreported.
        if final == proposal and final != candidate:
            bounded, log = bound_store(before, final, source='restored_llm')
            if log:
                trial.acquisitions18.append(log); final = bounded or 'wait'
        if execution_context.assess(before, final)['status'] == 'REJECT':
            # Reuse only S1's existing candidates and ordering. Generation runs
            # on a detached copy and cannot spend live budget or invent trials.
            alt = copy.deepcopy(before)
            alternatives = ([proposal] if proposal != final else [])+alt.alternatives(final)
            selected = None
            for action in alternatives:
                action, log = bound_store(alt, action, source='rejected_candidate_alternative')
                if log: trial.acquisitions18.append(log)
                if action and alt.assess(action)['status'] != 'REJECT':
                    selected = action; break
            final, reason = selected or 'wait', 'existing_S1_alternative_after_public_rejection'
        committed_trial = final == candidate
        committed = trial if committed_trial else before
        # FIFO queue edits express a public planning update; visit counters
        # express execution attempts and must match the eventual action.
        structured = trial.last_choice.get('structured_action')
        if not structured or (parse_action(structured).verb, parse_action(structured).target) != (parse_action(final).verb, parse_action(final).target):
            committed.visits = copy.deepcopy(before.visits)
        # Only the actually executed probe consumes exploration/trial credits.
        # Earlier discarded probes can have been cleared by Stage10 or P3.
        signature = lambda a: (parse_action(a).verb, parse_action(a).target)
        probe = next((r for r in reversed(trial.probe_candidates18) if signature(r['action']) == signature(final)), None) if committed_trial else None
        if not probe:
            for field in ('exploration_spent', 'trials', 'probes'):
                setattr(committed, field, copy.deepcopy(getattr(before, field)))
            committed.pending_probe = committed.explore_pending = None
        else:
            committed.exploration_spent = before.exploration_spent+1
            committed.pending_probe = copy.deepcopy(probe['pending'])
            committed.explore_pending = copy.deepcopy(probe['exploration'])
            if committed.pending_probe:
                committed.pending_probe['action'] = final
            if committed.explore_pending:
                committed.explore_pending['spent'] = committed.exploration_spent
            # Commit only that probe's speculative trial/inspection marker.
            p = parse_action(final)
            committed.trials = copy.deepcopy(before.trials)
            committed.probes = copy.deepcopy(before.probes)
            if p.verb == 'craft' and trial.trials.get(p.target, 0) > before.trials.get(p.target, 0):
                committed.trials[p.target] = before.trials.get(p.target, 0)+1
            if p.verb == 'inspect' and p.target in trial.probes:
                committed.probes[p.target] = copy.deepcopy(trial.probes[p.target])
        if not committed_trial:
            committed.selected_meta = None
            committed.audit16 = copy.deepcopy(trial.audit16)
            committed.audit16.update(selected=final, selected_module=None)
        committed.audit18 = dict(llm_proposal=proposal, original_s1_candidate=old_candidate,
            original_p1_candidate=original.audit16.get('P1_action'), original_p3_checks=original.audit16.get('checks'),
            bounded_candidate=candidate, final_action=final, reason=reason, assessments=checks,
            final_assessment=execution_context.assess(before, final, context), execution_context=context,
            acquisition_decisions=copy.deepcopy(trial.acquisitions18),
            changed_llm=final != proposal, changed_original_controller=final != old_candidate,
            original_controller_audit=copy.deepcopy(original.audit16),
            transaction=dict(committed_candidate_state=committed_trial, executed_probe=copy.deepcopy(probe),
                exploration_before=before.exploration_spent, exploration_after=committed.exploration_spent,
                trials_before=before.trials, trials_after=copy.deepcopy(committed.trials),
                fifo_before=before.queue, fifo_after=copy.deepcopy(committed.queue),
                dropped_probe_count=len(trial.probe_candidates18)-int(bool(probe)),
                attempt_history_unchanged=len(committed.attempt_log)==len(before.attempt_log),
                failures_unchanged=committed.failures10==before.failures10,
                selected_finish_intent=copy.deepcopy(committed.audit16.get('selected_module'))))
        committed.last_choice.update(action=final, reason=reason)
        self.__dict__ = copy.deepcopy(committed.__dict__)
        return final

    def observe(self, before, action, after):
        self.table.observe(before)
        frame = public_frame(self)
        old = set(self.table.recipes)
        # The inherited observation pipeline is invoked exactly once.
        super().observe(before, action, after)
        consequence = self.consequences.observe(before, action, after, frame, public_frame(self))
        self.outcome18 = dict(action=action, feedback=self.table.state['feedback'],
            consequence=consequence, new_recipe_names=sorted(set(self.table.recipes)-old),
            public_craft_success='successfully crafted' in self.table.state['feedback'],
            exploration_spent=self.exploration_spent, pending_probe=self.pending_probe,
            note='avoiding a rejected risk is a policy event, not a verified survival counterfactual')

    def to_dict(self):
        data = super().to_dict()
        data['consequences'] = self.consequences.to_dict()
        return copy.deepcopy(data)

    @classmethod
    def from_dict(cls, data):
        obj = cls()
        legacy = BaselineController.from_dict(data)
        obj.__dict__.update(legacy.__dict__)
        obj.consequences = ConsequenceMemory.from_dict(data['consequences'])
        return obj
