"""Review a whitespace-only evidence parser correction; do not apply it."""
import contextlib
import copy
import difflib
import io
import tempfile
import subprocess
from .common import *


def main():
    offline();check_freeze()
    commit=read(RESULTS/'execution.json')['freeze_commit']
    old=subprocess.check_output(['git','show',commit+':agents/agc/control.py'],cwd=ROOT,text=True)
    original="            if not any(quote in text for text in corpus):hard.append('goal_evidence_not_an_exact_public_quote')"
    replacement="            normalized_quote=' '.join(quote.split())\n            if not any(normalized_quote in ' '.join(text.split()) for text in corpus):hard.append('goal_evidence_not_an_exact_public_quote')"
    assert old.count(original)==1
    patch=''.join(difflib.unified_diff(old.splitlines(True),old.replace(original,replacement).splitlines(True),fromfile='a/agents/agc/control.py',tofile='b/agents/agc/control.py'))
    (REPORTS/'空白字符规范化候选修复.patch').write_text(patch)
    from scar.environment import restore,state_digest
    evidence=[]
    for game in GAMES:
        out=RESULTS/'runs'/f'{game}__AGC';p=out/'decision_exhausted.json'
        if not p.exists():continue
        d=read(p);attempt=d['decision']['attempts'][0];proposal=attempt['proposal'];q=proposal.get('goal_evidence','')
        state=d['decision']['control_before'];corpus=state['public_recent']+[d['observation']['text']]+[e['quote'] for e in (state['goal'] or {}).get('evidence',[])]
        whitespace=any(' '.join(q.split()) in ' '.join(x.split()) for x in corpus)
        with tempfile.TemporaryDirectory(prefix='scar24-quote-audit-') as tmp:
            env=restore(gzip.decompress((RESULTS/'initial'/game/'physical.pkl.gz').read_bytes()),tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                for r in rows(out/'trajectory.jsonl.gz'):
                    obs,reward,done,info=env.step({AGENT_ID:r['action']});env.update_scores(reward)
                    assert state_digest(env)==r['state_hash']
            assert env.obs[AGENT_ID]==d['observation']
            before=state_digest(env)
            with contextlib.redirect_stdout(io.StringIO()):obs,reward,done,info=env.step({AGENT_ID:proposal['action']});env.update_scores(reward)
            evidence.append(dict(game=game,step=d['step'],action=proposal['action'],quote=q,strict_reasons=attempt['reasons'],
                whitespace_equivalent_public_quote=whitespace,observation=d['observation'],before_hash=before,
                native_feedback=obs[AGENT_ID],native_reward=vars(reward[AGENT_ID]),invalid_action=bool(info.get('step_invalid_action',{}).get(AGENT_ID,False)),
                scope='Offline same-state one-action replay, no model call; not a resumed AGC run.'))
    receipt=dict(applied=False,new_model_calls=0,patch=str((REPORTS/'空白字符规范化候选修复.patch').relative_to(ROOT)),
        changed_file='agents/agc/control.py',removed_lines=1,added_lines=2,
        unchanged='No action/goal generation, no word/punctuation rewriting, no thresholds or game rules changed.',cases=evidence)
    target=RESULTS/'quote_correction_review.json'
    if target.exists():assert read(target)==receipt,'Historical review changed'
    else:write(target,receipt)
    print(json.dumps([dict(game=r['game'],step=r['step'],whitespace_match=r['whitespace_equivalent_public_quote'],native_invalid=r['invalid_action']) for r in evidence]))

if __name__=='__main__':main()
