"""Ablation of the explicit evidence packet, with the trigger/gate unchanged.

The original ledger still contains public evidence. This tests the structured
diagnosis versus generic reconsideration, not the value of all memory or the
trigger versus random extra calls. Endogenous numbers of triggers can differ.
"""
import json
from scar_public.continuation import ContinuationAgent


class GenericContinuationAgent(ContinuationAgent):
    def finalize_decision(self, executed, obs, step, prompt, query):
        def generic_query(user):
            marker='\nContinuation repair packet:\n'
            prefix,tail=user.split(marker,1)
            raw,_=json.JSONDecoder().raw_decode(tail)
            menu=dict(proposed_action=raw['trigger']['action'],goals=raw['goals'],options=raw['options'])
            return query(prefix+'\nReconsideration options:\n'+json.dumps(menu,ensure_ascii=False,sort_keys=True)+
                '\nReconsider the proposed action for the anchored public task. Select a useful next action '
                'from options, or retain the proposal if alternatives are worse. The goal is fixed; do not redefine it. '
                'Return reasoning, action, expected (a concrete observable change), and alternatives '
                '(at most 3 different candidate objects with those fields, in preference order). '
                'All candidates must serve the anchored goal. The menu avoids deliberate consumption; '
                'time, travel and danger still cost resources.')
        result=super().finalize_decision(executed,obs,step,prompt,generic_query)
        result['continuation']['evidence_exposure']='generic_reconsideration_with_original_ledger'
        return result
