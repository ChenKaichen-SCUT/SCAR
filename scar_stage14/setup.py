"""One-time historical protection and parser freeze; no experiment scores here."""
import datetime
import json
import subprocess
from pathlib import Path
from scar.io import atomic_json
from scar_stage14.common import ROOT,BASE,sha

def main():
    assert not (ROOT/'parser_freeze.json').exists()
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==BASE
    prior={p:sha(p) for p in subprocess.check_output(['git','ls-files','-z']).decode().split('\0') if p}
    atomic_json(ROOT/'prior_manifest.json',prior)
    files=['scar_stage14/__init__.py','scar_stage14/common.py','scar_stage14/knowledge.py','scar_stage14/annotations.py','scar_stage14/test_knowledge.py','scar_stage14/setup.py',str(ROOT/'parser_gold.json')]
    atomic_json(ROOT/'parser_freeze.json',{'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'base_commit':BASE,'hashes':{p:sha(p) for p in files},'protected_prior_files':len(prior),
        'no_model_api':True,'no_new_online_policy':True,'unknown_quantity_is_not_one':True,
        'knowledge_order':'native disclosures only through cutoff; K2 from original saved records; K3 presence is not causal utilization',
        'annotation':'manual labels independent of extraction code output; one analyst, no external blind annotation'})
    print(json.dumps({'protected_files':len(prior),'parser_frozen':True}))

if __name__=='__main__':main()
