"""Exact old-state quantity audit and engine provenance; offline evaluation only."""
import ast
import contextlib
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
from scar_unknown17.evaluate import one_action
from scar.io import atomic_json


def main():
    out=Path('results/unknown17');provenance=[];records=[]
    for game in ['saltglass','quarantine','robot_kingdom']:
        p=Path(os.environ['AGENTODYSSEY_ROOT'])/'games/generated'/game/'rules/action_rules.py'
        source=p.read_text();tree=ast.parse(source)
        for name in ['CraftRule','InspectRule']:
            node=next(n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name==name)
            provenance.append({'game':game,'rule':name,'file':str(p),'line':node.lineno,
                'file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'ast_sha256':hashlib.sha256(ast.dump(node).encode()).hexdigest()})
    with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for p in sorted((out/'families').glob('*.json')):
            family=json.loads(p.read_text())
            for b in family['batch_branches']:
                raw=gzip.decompress(Path(b['state']['path']).read_bytes())
                assert hashlib.sha256(raw).hexdigest()==b['state']['serialized_sha256']
                variants=[one_action(raw,f'craft {n} {b["target"]}',tmp) for n in [0,1,2,4]]
                records.append({'case_id':family['case_id'],'target':b['target'],'state':b['state'],'variants':variants})
    with gzip.open(out/'old_quantity_action_only.jsonl.gz','wt') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    result={'source_provenance':provenance,'states':len(records),'action_dispatches':4*len(records),
        'invalid_zero_rejected':all(v['actual_output']==0 and 'Invalid amount' in v['feedback'] for r in records for v in r['variants'] if v['action'].startswith('craft 0 ')),
        'clipping_examples':sum('Only enough ingredients' in v['feedback'] for r in records for v in r['variants']),
        'same_consumption_more_output_pairs':sum(r['variants'][1]['consumed']==r['variants'][2]['consumed'] and r['variants'][2]['actual_output']>r['variants'][1]['actual_output'] for r in records),
        'mechanism':'First reject if one nominal recipe is unavailable; then clip requested integer quantity by total available inputs. Deduct from hands, inventory, held containers in order, flooring each remaining count. Product goes to ground. Inspect exposes downstream products and ingredient names, not ingredient weights.',
        'policy_boundary':'Rule internals used solely in this evaluator; policies see only public text and observed deltas. No source rules or catalog imported by policies.',
        'api_calls':0}
    atomic_json(out/'engine_mechanisms.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'source_provenance','mechanism','policy_boundary'}}))

if __name__=='__main__':main()
