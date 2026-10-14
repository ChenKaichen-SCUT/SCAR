"""Final artifact consistency and secret exclusion checks; no API use."""
import math
from .common import *


def main():
    offline();integrity=check_freeze()
    metrics=read(RESULTS/'metrics.json');cost=read(RESULTS/'cost_reconciliation.json')
    assert read(RESULTS/'effective_completion.json')['complete']
    formal=[r for r in metrics if r['method']=='AGC-v2']
    assert len(formal)==3 and {r['game'] for r in formal}==set(GAMES)
    assert all(r['seed']==42 and r['actual_actions']==300 and r['status']=='step_limit' for r in formal)
    evidence=rows(RESULTS/'evidence_index.jsonl.gz')
    assert len(evidence)==900 and sum(len(e['requests']) for e in evidence)==cost['groups']['formal']['requests']
    assert len({q['request_id'] for e in evidence for q in e['requests']})==cost['groups']['formal']['requests']
    assert sum(r['requests'] for r in formal)==cost['groups']['formal']['requests']
    assert math.isclose(sum(r['cost_usd'] for r in formal),cost['groups']['formal']['cost_usd'],abs_tol=1e-12)
    for r in formal:
        c=r['counters']
        assert r['requests']==r['actual_actions']+c['action_retry_calls_executed']+c['confidence_review_calls_executed']
        assert c['controller_action_substitutions']==0
        receipt=read(RESULTS/'verification'/f"{case_id(r['game'],42)}.json")
        assert receipt['passed'] and receipt['exact_model_contexts']==r['requests'] and receipt['exact_native_steps']==300
    from scar.providers.deepseek import read_key
    secret=read_key(ROOT.parent/'miyao.txt').encode()
    assert secret
    paths=[]
    for folder in [ROOT/'agents/agc_v2',ROOT/'scar_stage25',RESULTS,REPORTS]:
        paths += [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    for p in paths:
        data=p.read_bytes()
        assert secret not in data,'private credential found'
        if p.suffix=='.gz':assert secret not in gzip.decompress(data),'private credential in compressed artifact'
        assert p.stat().st_size<50*1024*1024,(str(p),'oversize')
    exclusions={'artifact_manifest.json','artifact_audit.json','publication.json','change_accounting.json','Git变更记录.md'}
    manifest={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths) if p.name not in exclusions}
    write(RESULTS/'artifact_manifest.json',dict(files=manifest,metadata_excluded=sorted(exclusions)))
    result=dict(passed=True,formal_cases=3,cancelled_cases=6,native_steps_verified=900,
        exact_model_contexts_verified=cost['groups']['formal']['requests'],all_original_sources_unchanged=integrity,
        artifact_files=len(manifest),artifact_bytes=sum(x['bytes'] for x in manifest.values()),
        private_key_absent=True,downloaded_engine_not_in_stage25_artifacts=True,
        baseline_reruns=0,new_analysis_model_calls=0,checks='scores, costs, source freeze, action counts, complete response index, private key, sizes')
    write(RESULTS/'artifact_audit.json',result);print(json.dumps(result))


if __name__=='__main__':main()
