"""Typed evidence binding and bounded, blocker-specific model context."""
import copy
import json
from scar_stage20.evidence import snapshot as public_snapshot
from .public import shadow
from .config import MAX_PROMPT_CHARACTERS, MAX_EVIDENCE_RECORDS


def check(controller, proposal, *, require_prompt_ids=True):
    if require_prompt_ids and any(x not in controller.request_evidence20 for x in proposal['evidence_ids']):
        return dict(category='III', reason='evidence_not_in_current_request', hypothesis_accept=False)
    return shadow(controller, proposal)


def render(controller, obs, memory=None):
    public_snapshot(controller, obs)  # Full provenance registry; no hidden input.
    needed=controller.needed(); selected=[]
    records=[r for r in controller.evidence20.values() if r['snapshot_step']==obs['step']]
    records.sort(key=lambda r:(r['kind'] in ('goal','blocker'), not bool(set(r['names']) & needed),
        r['kind'] not in ('current_object','public_frontier','public_location'), r['kind'], r['key']))
    b={k:v for k,v in controller.blocker20.items() if k!='public_entries'}
    state={k:controller.table.state.get(k) for k in ('location','hands','equipment','ground')}
    prefix=('FINAL TASK: '+controller.objective[:500]+'\nBLOCKER: '+json.dumps(b,ensure_ascii=False)[:1200]+
        '\nCURRENT PUBLIC STATE: '+json.dumps(state,ensure_ascii=False)[:2200]+
        '\nRECENT PROBE RESULTS: '+json.dumps(controller.probe_log21[-2:],ensure_ascii=False)[:800]+
        '\nPUBLIC EVIDENCE (entry existence strict; relevance may be UNKNOWN):\n')
    lines=[]; size=len(prefix)
    for r in records:
        value=r['value']
        if isinstance(value,dict):
            value={k:v for k,v in value.items() if k in ('group','amount','location','counts','capacity','load','objects','route','from_location','ingredients','quantities','stations')}
        brief={k:r[k] for k in ('id','kind','key','names','observed_step')}; brief['value']=value
        line=json.dumps(brief,ensure_ascii=False,separators=(',',':'))
        if len(selected)>=MAX_EVIDENCE_RECORDS or size+len(line)+1>MAX_PROMPT_CHARACTERS:continue
        selected.append(copy.deepcopy(r)); lines.append(line); size+=len(line)+1
    controller.request_evidence20=[r['id'] for r in selected]
    prompt=prefix+'\n'.join(lines)
    assert len(prompt)<=MAX_PROMPT_CHARACTERS
    return prompt,dict(records=selected,rendered_records=lines,prompt_characters=len(prompt),
        snapshot_step=obs['step'],omitted_records=len(records)-len(selected),history_included=False)

