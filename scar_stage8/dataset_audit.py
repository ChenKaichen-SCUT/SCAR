"""Additional overlap characterization, not filtering or selection after freeze."""
import contextlib,json,tempfile
from pathlib import Path
from scar.io import atomic_json
from scar_stage8.build import shape
from scar_sequence.build import static_environment,dependency_graph

def main():
    cases=json.loads(Path('results/stage8/cases.json').read_text());old=[]
    for path in Path('results').rglob('cases.json'):
        if 'stage8' not in path.parts:old.extend(json.loads(path.read_text()))
    details=[]
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for g in sorted({c['game'] for c in cases if c['cohort']=='new'}):
            with tempfile.TemporaryDirectory() as tmp:
                env,_=static_environment(g,82000,tmp);past={c.get('goal',{}).get('object_id') for c in old if c.get('game')==g}
                reconstructed={}
                for target in past:
                    if target not in env.world.objects or not env.world.objects[target].craft_ingredients:continue
                    try:graph,*_=dependency_graph(env,target);reconstructed[target]=shape(graph,target)
                    except ValueError:pass
                for c in cases:
                    if c['cohort']!='new' or c['game']!=g:continue
                    target=c['goal']['object_id'];s=shape(c['recipe_graph'],target)
                    same_names=sorted({x.get('game') for x in old if x.get('goal',{}).get('name')==c['goal']['name']})
                    matches=sorted(x for x,h in reconstructed.items() if h==s)
                    details.append({'case_id':c['id'],'game':g,'target_name':c['goal']['name'],'same_name_in_prior_sourcegames':same_names,
                        'same_game_target_overlap':target in past,'all_prior_same_game_targets_reconstructed':len(reconstructed),
                        'anonymous_shape_matches_prior_targets':matches,'initial_snapshot_differs_from_all_old':not any(c['state_hash']==x.get('state_hash') for x in old),
                        'same_public_history':any(c['history']==x.get('history') for x in old),
                        'scope':'extended characterization using native recipes for older datasets without archived graphs; no reselection'})
    atomic_json('results/stage8/extended_overlap_audit.json',{'records':details,'new_test_selection_changed':False,'API_calls':0,
        'all_new_targets_and_states':all(not x['same_game_target_overlap'] and x['initial_snapshot_differs_from_all_old'] and not x['same_public_history'] for x in details)})
    print(json.dumps(details))
if __name__=='__main__':main()
