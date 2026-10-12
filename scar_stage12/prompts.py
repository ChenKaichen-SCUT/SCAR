"""Frozen Stage A query construction; only whitelisted public fields."""
import json
from scar_stage11.controller import PROMPT_REMINDER

J3_INSTRUCTION = '''Choose an exploration direction for the stated task using only the observations and confirmed public relations below. Consider all listed candidates, including currently unconnected visible materials. Do not assume that semantic resemblance guarantees a hidden recipe. A hypothesis is not known game knowledge. You may express uncertainty. Each candidate uses the SAME public-only executor for at most 4 actions including preparation and inspection. Historical locations are not guarantees of current presence.
Return one JSON object with selected_candidate_id, ranked_candidate_ids (up to three distinct menu IDs in best-first order, use all if fewer than three exist, selected ID first), reason, hypothesized_connection, confidence (number from0 to1), expected_information, alternative_if_failed (another menu ID or null). Keep each text field below30 words. Do not invent candidate IDs or assert unobserved input names as confirmed. Select the best available candidate even if all offer weak information; explain uncertainty. No other text.'''


def messages(state, method):
    assert method in {'J2', 'J3'}
    system = state['base_system']+'\n'+PROMPT_REMINDER+'\n'+state['facts_text']
    common = {'recent_memory_STM5': state['memory'], 'observation': state['observation'],
              'public_knowledge': state['public_view']}
    if method == 'J2':
        instruction = 'Choose the next single game action. Return a JSON object with action and reasoning. Use only public evidence. Keep reasoning concise.'
    else:
        common['exploration_candidates'] = state['candidates']
        instruction = J3_INSTRUCTION
    return system, json.dumps(common, ensure_ascii=False, separators=(',', ':'))+'\n'+instruction


def validate(parsed, method, candidates):
    ids = {c['id'] for c in candidates}; errors = []
    if method == 'J2':
        if not isinstance(parsed.get('action'), str) or not parsed['action'].strip():
            errors.append('missing_action')
        return errors
    required = ['selected_candidate_id', 'ranked_candidate_ids', 'reason', 'hypothesized_connection',
                'confidence', 'expected_information', 'alternative_if_failed']
    errors += ['missing_'+key for key in required if key not in parsed]
    if not isinstance(parsed.get('selected_candidate_id'), str) or parsed['selected_candidate_id'] not in ids:
        errors.append('selected_outside_menu')
    ranked = parsed.get('ranked_candidate_ids')
    if (not isinstance(ranked, list) or len(ranked) != min(3, len(ids)) or
            not all(isinstance(i, str) and i in ids for i in ranked) or len(set(ranked)) != len(ranked)):
        errors.append('invalid_ranking')
    elif ranked[0] != parsed.get('selected_candidate_id'):
        errors.append('selected_not_rank1')
    confidence = parsed.get('confidence')
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append('invalid_confidence')
    if parsed.get('alternative_if_failed') is not None and (not isinstance(parsed.get('alternative_if_failed'), str) or parsed['alternative_if_failed'] not in ids):
        errors.append('invalid_alternative')
    return errors
