"""One prediction and one final choice; risk never gates execution."""
import json

REFLECTION_SYSTEM='''You predict the consequences of one proposed action in a partially observed environment.
Use only the supplied public observations, history, task summary and action interface. Do not invent game rules or hidden state.
Predict the immediate state change, whether it harms the actual goal, any new blocking conditions, and whether a safer alternative exists.
Distinguish an acquisition goal from one possible production method; distinguish temporary recoverable changes from irreversible loss.
State uncertainty when the evidence is insufficient. This is advice, never a prohibition or a replacement decision.
Return exactly a JSON object with string fields predicted_effect, goal_risk (low, medium, or high), and reason.
Include blocking conditions, recoverability and alternative considerations in reason when supported by public evidence.'''

def augment(prompt,summary):return prompt+'\n\nSAER public task state:\n'+json.dumps(summary,ensure_ascii=False)

def parse_prediction(text):
    try:p=json.loads(text)
    except (ValueError,TypeError):return None
    if not isinstance(p,dict) or p.get('goal_risk') not in ['low','medium','high']:return None
    if not all(isinstance(p.get(k),str) and p[k].strip() for k in ['predicted_effect','reason']):return None
    return {k:p[k] for k in ['predicted_effect','goal_risk','reason']}

def calibrate(candidate,base_prompt,system_prompt,summary,call):
    # The same input builder is used for fixed-candidate diagnostics and online.
    context=augment(base_prompt,summary)
    reflection_user=json.dumps(dict(original_decision_input=context,original_public_interface=system_prompt,candidate=candidate),ensure_ascii=False)
    predicted=call('reflection',reflection_user,REFLECTION_SYSTEM);prediction=parse_prediction(predicted['response'])
    warning=bool(prediction and prediction['goal_risk'] in ['medium','high'])
    feedback=dict(candidate=candidate,prediction=prediction,warning=warning,
        prediction_status='available' if prediction else 'unavailable_or_malformed',
        instruction='Make the final decision using the original action JSON format. This prediction is fallible advice. '
        'You may keep the candidate, including a high-risk candidate, if appropriate for the goal and available evidence. '
        'No action is forbidden and no replacement action is prescribed. If prediction is unavailable, use the original evidence.')
    final=call('final',context+'\n\nSAER consequence reflection:\n'+json.dumps(feedback,ensure_ascii=False),system_prompt)
    return final,dict(candidate=candidate,task_summary=summary,prediction=prediction,warning=warning,
        prediction_response=predicted['response'],final_response=final['response'],risk_veto=False)
