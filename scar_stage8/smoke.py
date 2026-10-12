"""Zero-API validation of postprocessors against all five real runner smokes."""
import argparse,json
from pathlib import Path
from scar.io import atomic_json
from scar_stage8.evaluate import audit_episode
from scar_stage8.decision_audit import audit
from scar_stage8.analyze import reliability

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();records=[]
    for folder in sorted((Path(a.runtime)/'integration/runs').iterdir()):
        task=json.loads((folder/'task.json').read_text())['task']
        resources=audit_episode((str(folder),task));decisions=audit((str(folder),task))
        rows=[json.loads(p.read_text()) for p in sorted((folder/'steps').glob('*/transition.json'))];rel=reliability(rows,task)
        records.append({'method':task['algorithm'],'actions':len(rows),'resources':len(resources['resource']),'comparisons':len(decisions['records']),
            'reproduction_errors':decisions['reproduction_errors'],'metrics_computed':bool(rel)})
    result={'records':records,'API_calls':0,'passed':len(records)==5 and all(not r['reproduction_errors'] and r['comparisons']==r['actions']*5 for r in records)}
    atomic_json('results/stage8/analysis_smoke_checks.json',result);print(json.dumps(result));assert result['passed']
if __name__=='__main__':main()
