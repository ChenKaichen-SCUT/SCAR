"""Archive generated native initial states and final agent memories, no weights."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
from .config import RESULTS,GAMES,METHODS,ENGINE
from .analyze import read,write


def archive_bytes(path, data):
    # Keep verified static archive bytes stable across packaging invocations.
    if path.exists() and gzip.decompress(path.read_bytes()) == data:
        return
    path.write_bytes(gzip.compress(data, mtime=0))


def differences(a,b,path=''):
    if type(a)!=type(b):yield dict(path=path,left=a,right=b)
    elif isinstance(a,dict):
        for key in sorted(a.keys()|b.keys()):
            if key not in a or key not in b:yield dict(path=path+'/'+key,left=a.get(key),right=b.get(key))
            else:yield from differences(a[key],b[key],path+'/'+key)
    elif isinstance(a,list):
        if a!=b:yield dict(path=path,left=a,right=b)
    elif a!=b:yield dict(path=path,left=a,right=b)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',required=True);args=parser.parse_args()
    runtime=Path(args.runtime);comparisons=[]
    for game in GAMES:
        states=[];public=[]
        for method in METHODS:
            source=runtime/'runs'/f'{game}__{method}';dest=RESULTS/'runs'/source.name;dest.mkdir(parents=True,exist_ok=True)
            initial=source/'initial/config.json'
            archive_bytes(dest/'native_prebootstrap_config.json.gz',initial.read_bytes())
            states.append(read(initial));public.append(read(source/'initial_public.json')['observation'])
            if (dest/'summary.json').exists():
                for p in (source/'memory').glob('*'):
                    if p.suffix not in ('.json','.txt'):continue
                    out=dest/'final_memory';out.mkdir(exist_ok=True)
                    archive_bytes(out/(p.name+'.gz'),p.read_bytes())
        assert len({json.dumps(x,sort_keys=True) for x in public})==1
        for method,state in zip(METHODS,states):
            diff=list(differences(states[0],state))
            for row in diff:
                row['unordered_same_members']=isinstance(row['left'],list) and isinstance(row['right'],list) and sorted(row['left'])==sorted(row['right'])
            assert all(row['path'].startswith('/world/auxiliary/ing_to_obj_map/') and row['unordered_same_members'] for row in diff),diff
            comparisons.append(dict(game=game,reference_method=METHODS[0],method=method,
                         initial_public_observation_identical=True,differences=diff,
                         caveat='Saved pre-bootstrap physical contents are identical except recipe presentation order; this order is not controlled across processes and can affect later LLM contexts.'))
    write(RESULTS/'initial_state_comparison.json',dict(passed=True,comparisons=comparisons,
          byte_identical_state=False,same_prebootstrap_contents_except_recipe_list_order=True,
          fixed_environment_seed=42,pythonhashseed_pinned=False,api_calls=0))
    # Bootstrap parameters are write-once scenario samples. Extract key names
    # structurally from the official bootstrap, never from an agent trajectory.
    import ast
    scenarios=[]
    for game in GAMES:
        tree=ast.parse((ENGINE/f'games/generated/{game}/rules/step_rules/main_quest.py').read_text())
        fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_bootstrap')
        keys={n.slice.value for n in ast.walk(fn) if isinstance(n,ast.Subscript) and isinstance(n.ctx,ast.Store)
              and isinstance(n.value,ast.Attribute) and n.value.attr=='_generated'
              and isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,str)}
        records={}
        for method in METHODS:
            source=runtime/'runs'/f'{game}__{method}'/'config.json'
            generated=read(source)['world']['auxiliary'].get('main_quest',{}).get('generated',{})
            records[method]={k:generated[k] for k in sorted(keys) if k in generated}
        variation=[k for k in sorted(keys) if len({json.dumps(r.get(k),sort_keys=True) for r in records.values()})>1]
        scenarios.append(dict(game=game,bootstrap_keys=sorted(keys),records=records,
                              varying_keys=variation,identical_scenario_parameters=not variation))
    write(RESULTS/'generated_scenario_comparison.json',dict(games=scenarios,api_calls=0,
          caveat='Same environment seed does not remove hash-randomized set-order tiebreaking in the official bootstrap.'))


if __name__=='__main__':main()
