"""Compare independently regenerated server diagnostics without transferring data."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
from scar.io import atomic_json
from scar_stage14.common import ROOT,sha,load


DERIVED=['episode_timeline.jsonl.gz','episode_knowledge_summary.json','frozen_state_knowledge.json',
    'history_time_audit.json','request_context_audit.json','branch_knowledge_timeline.jsonl.gz','branch_knowledge_summary.json',
    'episode_knowledge_events.jsonl.gz','knowledge_statistics.json','parser_validation.json',
    'disclosure_registration_by_format_action.json','intent_knowledge_timeline.jsonl.gz','candidate_window_metrics.jsonl.gz',
    'calibrated_state_metrics.json','calibrated_method_metrics.json','family_metrics.json','paired_family_comparisons.json',
    'calibrated_coverage.json','comparison_strata.json','intent_interpretation_summary.json','residual_states.json',
    'continuity_audit.json','full_episode_failure_audit.json','full_reference_commitments.json','residual_summary.json',
    'residual_witness_audit.json','residual_witness_summary.json',
    'residual_witness_knowledge_timeline.jsonl.gz','full_reference_commitments_final.json']


def main(host,root,all_files=False):
    if all_files:expected=load(ROOT/'artifact_manifest.json')['files']
    else:
        files=[ROOT/f for f in DERIVED]+sorted(Path('reports/stage14').rglob('*.md'))
        expected={str(p):sha(p) for p in files}
    code="import sys,json,hashlib;from pathlib import Path; x=json.load(sys.stdin); print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in x}))"
    command='cd '+shlex.quote(root)+' && python3 -c '+shlex.quote(code)
    result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ControlPath=/tmp/scar-ssh-%C',host,command],input=json.dumps(list(expected)),text=True,capture_output=True,check=True)
    actual=json.loads(result.stdout);mismatch=[p for p,h in expected.items() if actual.get(p)!=h]
    assert not mismatch,mismatch
    if not all_files:
        result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ControlPath=/tmp/scar-ssh-%C',host,
            'cat '+shlex.quote(root+'/results/stage14/residual_checkpoint_manifest.json')],text=True,capture_output=True,check=True)
        remote=json.loads(result.stdout);local=load(ROOT/'residual_checkpoint_manifest.json')
        physical=[]
        for a,b in zip(local,remote):
            assert {k:v for k,v in a.items() if k!='snapshot_sha256'}=={k:v for k,v in b.items() if k!='snapshot_sha256'}
            physical.append({'state_id':a['state_id'],'physical_hash':a['physical_hash'],'public_prefix_exact':True,
                'local_snapshot_sha256':a['snapshot_sha256'],'server_snapshot_sha256':b['snapshot_sha256']})
        assert len(physical)==22
        atomic_json(ROOT/'server_verification.json',{'passed':True,'files':len(expected),'hashes':actual,
            'scope':'independently recomputed chronological audits, metrics, residual analyses and reports',
            'independent_checkpoint_physical_checks':physical,
            'snapshot_byte_difference':'trusted cloudpickle includes run_dir/config_path temporary paths; physical state and all branch effects must match, serialization bytes need not',
            'native_verification':'separate server/local double replay certificates','api_calls':0})
    print({'passed':True,'files':len(expected),'all_manifest_files':all_files})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--root',required=True);p.add_argument('--all',action='store_true');a=p.parse_args()
    main(a.host,a.root,a.all)
