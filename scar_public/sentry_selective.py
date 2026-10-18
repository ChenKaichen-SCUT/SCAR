"""Compare an ordinary proposal with a grounded repair; keep by default.

The model judges semantic support. Code checks provenance, current context,
explicit decision predicates and freshness, NOT semantic entailment or success.
No entity names, game-specific rules or evaluation outcomes enter this policy.
"""
import json
from scar_public.sentry_persistent import PersistentRepair, fingerprint, action_valid

INSTRUCTION = '''Assess two actions symmetrically in the SAME current state.
The candidate labels encode only lexical order, NOT quality, priority or source.
Neither candidate is preferred. Use only the supplied public history and action
schema. The task text is a working hypothesis, not an authoritative new goal.

For EACH action separately distinguish its PURPOSE from its CURRENT CONDITIONS.
An action can serve a useful prerequisite yet be blocked now. Preparation is
reasonable only when its own immediate conditions permit it. Conversely, a
preparatory action need not guarantee the entire downstream plan to be useful.
Assess movement as movement, acquisition as acquisition, etc.; do not transfer
the preconditions of a later action to its prerequisite. Historical location
and quantities may be stale. Use latest observations for current dynamic facts.

status=blocked requires a SPECIFIC observed defect: failed_precondition,
repeated_failure with unchanged relevant conditions, resource_conflict with a
still required resource, or contradicts_goal. Do not invent a defect from lack
of proof of ultimate success. status=supported means its immediate enabling
conditions are supported and it serves the task, including a useful prerequisite.
Use unknown for unresolved enabling facts. This is a fallible semantic judgment,
not a proof. Never invent requirements (e.g. holding vs nearby access) absent
from supplied action descriptions or observed failures/successes.

Then assess whether either action addresses the OTHER action's specific defect:
it can change that condition, be an enabled upstream step toward changing it,
or acquire information whose possible outcomes choose DIFFERENT subsequent
actions. A known missing precondition does not become a useful test merely
because repeating failure is observable. A test needs unresolved alternatives
and different continuations. Describe those continuations in how when relevant.
Do not equate any executable detour with a repair. Check consumption and retained
task resources. Unknown downstream success is distinct from unknown current
applicability or resource conflict. State these uncertainties separately.

Cite literal OBSERVATION substrings, never candidate reasoning or action text.
Give current-cycle context for a supported alternative, and explain persistence
of any older facts. Do not paraphrase quotes. Do not output a third action.
Exactly:
{"candidates":[{"id":"A","purpose":"task/prerequisite role",
"status":"supported|blocked|unknown","defect_kind":"none|failed_precondition|repeated_failure|resource_conflict|contradicts_goal",
"condition":"immediate condition assessment and uncertainty",
"evidence":[{"cycle":0,"quote":"literal observation substring"}]},
{"id":"B","purpose":"...","status":"...","defect_kind":"...","condition":"...","evidence":[]}],
"relations":[{"blocked":"A","alternative":"B","addresses_issue":true,
"how":"how the enabled alternative addresses that specific defect; remaining downstream uncertainty",
"resources":"preserved|conflict|unknown","resource_reason":"consumption and retained requirements",
"evidence":[{"cycle":0,"quote":"literal observation substring"}]}]}
List a relation only for a blocked candidate; relations may be empty. Use the
actual A/B identifiers, in either direction. Keep explanations concise.
'''


def _text(obj, keys):
    if any(not isinstance(obj.get(k),str) or not obj[k].strip() for k in keys):
        raise ValueError('missing explanation')


def _references(refs, records):
    lookup={r['cycle']:r['observation'] for r in records}
    if not isinstance(refs,list) or not refs:raise ValueError('missing observation support')
    for ref in refs:
        if not isinstance(ref,dict) or set(ref)!={'cycle','quote'}:raise ValueError('invalid reference')
        cycle,quote=ref['cycle'],ref['quote']
        if type(cycle) is not int or cycle not in lookup or not isinstance(quote,str) or len(quote.strip())<12:
            raise ValueError('invalid reference')
        if quote not in lookup[cycle]:raise ValueError('quote absent from observation')


def replacement_allowed(verdict, records, ordinary_id='A'):
    if not isinstance(verdict,dict) or set(verdict)!={'candidates','relations'}:
        raise ValueError('fixed comparison fields required')
    candidates=verdict['candidates'];relations=verdict['relations']
    if not isinstance(candidates,list) or len(candidates)!=2 or not isinstance(relations,list):
        raise ValueError('two independent assessments required')
    for item in candidates:
        if not isinstance(item,dict) or set(item)!={'id','purpose','status','defect_kind','condition','evidence'}:
            raise ValueError('fixed assessment fields required')
        _text(item,['purpose','condition'])
        if item['status'] not in ('supported','blocked','unknown'):raise ValueError('invalid status')
    if {i['id'] for i in candidates}!={'A','B'}:raise ValueError('distinct candidate identities required')
    indexed={i['id']:i for i in candidates};original=indexed[ordinary_id];alt_id='B' if ordinary_id=='A' else 'A';alt=indexed[alt_id]
    if original['status']!='blocked':return False,'ordinary_without_supported_defect'
    if original['defect_kind'] not in ('failed_precondition','repeated_failure','resource_conflict','contradicts_goal'):
        raise ValueError('specific ordinary defect required')
    _references(original['evidence'],records)
    if alt['status']!='supported':return False,'alternative_not_ready'
    if alt['defect_kind']!='none':return False,'alternative_has_defect'
    _references(alt['evidence'],records)
    if records[-1]['cycle'] not in [r['cycle'] for r in alt['evidence']]:
        raise ValueError('current alternative context required')
    for r in relations:
        if not isinstance(r,dict) or set(r)!={'blocked','alternative','addresses_issue','how','resources','resource_reason','evidence'}:
            raise ValueError('fixed relation fields required')
    matching=[r for r in relations if r['blocked']==ordinary_id and r['alternative']==alt_id]
    if len(matching)!=1:return False,'no_specific_repair_relation'
    relation=matching[0];_text(relation,['how','resource_reason']);_references(relation['evidence'],records)
    if relation['addresses_issue'] is not True:return False,'unrelated_alternative'
    if relation['resources']!='preserved':return False,'resource_support_missing'
    return True,'supported_comparison'


class SelectiveRepair(PersistentRepair):
    def __init__(self,provider,system,max_calls=30,burst=6,max_comparisons=30):
        super().__init__(provider,system,'advice',max_calls,burst)
        self.mode='selective';self.comparisons=0;self.max_comparisons=max_comparisons

    def choose(self,step,observation,proposed):
        pending=self.pending;chosen=proposed;verdict=None;errors=[];ordinary_id=None
        eligible=bool(pending and pending['step']==step and pending['observation_hash']==fingerprint(observation))
        reason='no_fresh_repair'
        if eligible:
            alternative=pending['card']['next']['action']
            if alternative.strip()==proposed['action'].strip():reason='same_action'
            elif not action_valid(alternative,self.system):reason='invalid_repair_action'
            elif self.comparisons>=self.max_comparisons:reason='comparison_budget'
            else:
                # Source-blind canonical pair: swapping ordinary/repair roles
                # produces exactly the same request, including ordering. Their
                # persuasive rationales cannot bias applicability assessments.
                candidates=[dict(id=label,action=action) for label,action in zip(('A','B'),sorted((proposed['action'],alternative)))]
                ordinary_id=next(c['id'] for c in candidates if c['action']==proposed['action'])
                packet=dict(action_schema=self.system,history=self.records,current_cycle=self.records[-1]['cycle'],
                    current_observation=observation,task_hypothesis=pending['card']['goal'],candidates=candidates)
                self.comparisons+=1
                result=self.provider.request([{'role':'system','content':INSTRUCTION},
                    {'role':'user','content':json.dumps(packet,ensure_ascii=False)}],repair=300,
                    options={'temperature':0.0,'max_tokens':2048,'response_format':{'type':'json_object'}})
                try:
                    output=result['choices'][0]
                    if output.get('finish_reason')!='stop':raise ValueError('incomplete comparison')
                    verdict=json.loads(output['message']['content'])
                    replace,reason=replacement_allowed(verdict,self.records,ordinary_id)
                    if replace:
                        issue=next(c for c in verdict['candidates'] if c['id']==ordinary_id)
                        relation=next(r for r in verdict['relations'] if r['blocked']==ordinary_id)
                        chosen=dict(action=alternative,reasoning=issue['condition']+' '+relation['how'])
                except (ValueError,KeyError,TypeError) as exc:
                    errors.append(str(exc));reason='invalid_comparison'
        self.events.append(dict(type='persistent_choice',step=step,eligible=eligible,mode=self.mode,
            proposed=proposed['action'],chosen=chosen['action'],changed=chosen['action']!=proposed['action'],
            selection_reason=reason,comparison=verdict,ordinary_id=ordinary_id,comparison_errors=errors,comparison_calls=self.comparisons))
        return chosen
