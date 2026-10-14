"""Public interface diagnostics; never invent arguments or replace an action."""
import json
import shlex

CONTRACT = ('Action interface requirements: use one exact public verb and supply every positional '
    'parameter in the documented order. A parameter containing spaces must be quoted inside the '
    'action string (escape those quotes correctly in JSON). Environment hints describe objectives, '
    'not necessarily complete command strings. Do not invent a missing object or silently omit '
    'an argument. If the needed argument is not supported by observation, choose a syntactically '
    'complete action yourself using the available public evidence. Return the original action JSON fields.')

def signature(spec):
    return ' '.join([spec.verb,*['<'+p+'>' for p in spec.params]])

def diagnose(proposal,actions):
    issues=[]
    if not isinstance(proposal,dict):return dict(issues=['response_is_not_a_JSON_object'],previous_proposal=proposal)
    action=proposal.get('action')
    if not isinstance(action,str):issues.append('action_must_be_a_string')
    else:
        action=action.strip();spec=next((s for s in sorted(actions,key=lambda a:len(a.verb),reverse=True) if action==s.verb or action.startswith(s.verb+' ')),None)
        if spec is None:
            issues.append(dict(error='unknown_public_verb',allowed_signatures=[signature(s) for s in actions]))
        else:
            try:args=shlex.split(action[len(spec.verb):])
            except ValueError as exc:issues.append(dict(error='unbalanced_argument_quotes',detail=str(exc),required_signature=signature(spec)))
            else:
                if len(args)!=len(spec.params):
                    issues.append(dict(error='wrong_argument_count',required_signature=signature(spec),parameter_names=list(spec.params),
                        expected_argument_count=len(spec.params),actual_argument_count=len(args),received_arguments=args))
    goal=proposal.get('goal_description')
    if not isinstance(goal,str) or not goal.strip() or len(goal)>400:issues.append('goal_description_must_be_a_nonempty_string_of_at_most_400_characters')
    return dict(issues=issues,previous_proposal=proposal) if issues else None

def with_interface_feedback(prompt,previous):
    text=prompt+'\n\n'+CONTRACT
    if previous:
        text+='\n\nPrevious returned proposal failed interface validation:\n'+json.dumps(previous,ensure_ascii=False)
        text+='\nCorrect the stated format problem. No argument value or replacement action has been supplied by the controller.'
    return text
