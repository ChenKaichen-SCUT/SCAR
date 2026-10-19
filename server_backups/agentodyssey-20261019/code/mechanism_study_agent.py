"""Per-process adapters; do not edit frozen v3 files or historical baselines."""
import os
from functools import lru_cache
from agents import feedback_v3_agent as frozen
from agents.mechanism_study_core import StudyLedger,VARIANTS

VARIANT=os.environ.get('AO_STUDY_VARIANT','full_reference')
if VARIANT=='v4_selected':
    from agents.feedback_v4_core import Ledger
    import json
    DISABLED=set(json.loads(os.environ.get('AO_DISABLED_COMPONENTS','[]')))
else:Ledger=StudyLedger;DISABLED=VARIANTS[VARIANT]
frozen.Ledger=Ledger

if 'dependency_execution' in DISABLED:
    frozen.REVIEW_SYSTEM=frozen.REVIEW_SYSTEM.replace('The ledger dispatches short preparation steps through observed recipes, containers, routes and capacities.','Automatic preparation and committed-path execution are disabled. You must propose each next preparation using the observed recipes, containers, routes and capacities.')
    frozen.ACTOR_INSTRUCTION=frozen.ACTOR_INSTRUCTION.replace('The dispatcher can execute a known necessary preparation before your proposal, or reject it; read prior interventions. Each path is short and will be rechecked against fresh observation after each action.','Only the first admissible action in the newly proposed alternatives is selected. Automatic preparation and committed-path execution are disabled; propose the next action anew using current observations.')
if 'hard_repeat' in DISABLED:
    frozen.ACTOR_INSTRUCTION=frozen.ACTOR_INSTRUCTION.replace('repeated unchanged inspection is rejected','repeated unchanged inspection is reported as an advisory warning')
if 'hypothesis' in DISABLED:
    lines=[]
    for line in frozen.REVIEW_SYSTEM.splitlines():
        if line.startswith(('Optional hypotheses','At most two hypotheses')):continue
        if line.startswith('Return JSON:'):
            line='Return JSON: {"diagnosis":"...","focus_task_id":"existing pending id","next_action_rationale":"...","objective":{"action":"terminal action in declared format","reason":"how it satisfies the main task","evidence":[{"step":1,"quote":"exact source >=8 chars"}]}}.'
        lines.append(line)
    frozen.REVIEW_SYSTEM='\n'.join(lines)
    frozen.ACTOR_INSTRUCTION=frozen.ACTOR_INSTRUCTION.replace(', and optional test_id','').replace('For causal tests, supply an explicit valid test_id only when the test\'s preconditions hold and its expected effect is observable. Otherwise perform a preparation without a test label.','Use observed task effects to assess progress; the separate hypothesis module is disabled.')
if VARIANT=='v4_selected':
    notice='''\nReliability corrections: unreported inventory in darkness is unknown, not empty. Capacity refusals are conditional evidence, never a zero-capacity universal rule. Death and explicit rule changes invalidate old operational constraints. Treat an observed non-equippable object as non-equippable; many held weapons already satisfy the environment task. Accept observed stage completion over a guessed requirement to equip. Do not hold an objective that current evidence contradicts. A successful navigation edge may be needed again for a new goal or retreat; repeated unchanged investigations are different from returning to safety. Fresh actor proposals take priority over an old queue when the context changed.'''
    frozen.REVIEW_SYSTEM+=notice;frozen.ACTOR_INSTRUCTION+=notice

class MechanismStudyAgent(frozen.FeedbackV3Agent):
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw)
        if 'hypothesis' in DISABLED:self.actor_system=self.actor_system.replace('; test_id is optional','')
    def emit(self,r):
        if r.get('event') in ['decision','controller','algorithm_stalled']:r=dict(r,study_variant=VARIANT,disabled_components=sorted(DISABLED))
        super().emit(r)

@lru_cache(maxsize=None)
def create_mechanism_study_agent(Agent):
    return type('MechanismStudyAgent__'+Agent.__module__+'.'+Agent.__name__,(MechanismStudyAgent,Agent),{'__module__':Agent.__module__,'__agent__':Agent})
