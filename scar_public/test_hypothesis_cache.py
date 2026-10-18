import hashlib
import json
import pytest
from scar_public.experiments.continuation_branch import ReusingProvider


def test_layered_cache_requires_same_step_payload_and_repair_and_prefers_baseline(tmp_path):
    baseline=tmp_path/'baseline';extra=tmp_path/'h1'
    baseline.mkdir();extra.mkdir()
    p=ReusingProvider(tmp_path/'new',tmp_path/'unused.key',historical=baseline,additional_historical=[extra])
    p.step=49;p.cache_only=True
    messages=[dict(role='user',content='Only the current public state.')]
    payload=dict(model=p.model,messages=messages,temperature=.7,top_p=.8,presence_penalty=0,
        max_tokens=1536,thinking={'type':'disabled'},response_format={'type':'json_object'})
    h=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    name=f'0049-0-{h[:16]}.response.json'
    (extra/name).write_text(json.dumps({'cached':'h1'}))
    assert p.request(messages)=={'cached':'h1'}
    for step,repair,msg in [(50,0,messages),(49,1,messages),(49,0,[dict(role='user',content='changed state')])]:
        p.step=step
        with pytest.raises(RuntimeError):p.request(msg,repair)
    p.step=49;(baseline/name).write_text(json.dumps({'cached':'baseline'}))
    assert p.request(messages)=={'cached':'baseline'}
    hits=[json.loads(x) for x in (p.directory/'historical_reuse.jsonl').read_text().splitlines()]
    assert [x['source'] for x in hits]==[str(extra),str(baseline)]
