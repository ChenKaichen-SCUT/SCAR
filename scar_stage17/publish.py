"""Publish only verified Stage17 artifacts after both native replays finish."""
import gzip
import re
import subprocess
from .common import ROOT,RESULTS,load,write,sha,METHODS
from .run import check_freeze


def main():
    check_freeze()
    assert load(RESULTS/'analysis.json')['complete']
    for site in ('server','local'):
        replay=load(RESULTS/f'replay_{site}.json');assert replay['passed'] and replay['trajectory_count']==120
    left=load(RESULTS/'replay_local.json')['runs'];right=load(RESULTS/'replay_server.json')['runs']
    assert left==right
    old=load(RESULTS/'prior_manifest.json')['files'];assert all(sha(ROOT/p)==h for p,h in old.items())
    write(RESULTS/'research_state.json',dict(phase='completed_verified_ready_to_publish',formal_started=True,total_runs=120,server_local_replay_equal=True,internal_horizon=100))
    paths=[]
    for directory in ('scar_stage17','third_party_adapters','results/stage17','reports/stage17'):
        for p in (ROOT/directory).rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc':continue
            assert p.stat().st_size<95*1024*1024,'Artifact exceeds GitHub file size limit'
            assert p.suffix not in ('.pkl','.sqlite'), 'Runtime state/database must not be published'
            text=gzip.decompress(p.read_bytes()).decode() if p.suffix=='.gz' else p.read_text()
            assert not re.search(r'\bsk-[A-Za-z0-9_-]{20,}',text),'Potential secret in '+str(p)
            paths.append(str(p.relative_to(ROOT)))
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    assert all(p.startswith(('scar_stage17/','third_party_adapters/','results/stage17/','reports/stage17/')) for p in staged),'Unrelated staged changes; defer publication'
    write(RESULTS/'publication_manifest.json',dict(files={p:sha(ROOT/p) for p in paths if not p.endswith('publication_manifest.json')},
        verified_runs=120,server_local_replay_equal=True,historical_unchanged=len(old),secret_scan_passed=True))
    subprocess.run(['git','add','--','scar_stage17','third_party_adapters','results/stage17','reports/stage17'],cwd=ROOT,check=True)
    subprocess.run(['git','commit','-m','Report frozen Stage17 five-method native crafting comparison'],cwd=ROOT,check=True)
    subprocess.run(['git','-c','http.proxy=','-c','http.lowSpeedLimit=1000','-c','http.lowSpeedTime=30','push','origin','main'],cwd=ROOT,check=True)
    print('Published',subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())

if __name__=='__main__':main()
