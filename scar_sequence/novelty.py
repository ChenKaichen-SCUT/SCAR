"""Source/object and coarse recipe-tree overlap with all prior hard cases."""
import json
from pathlib import Path
from scar.io import atomic_json


def shape(case):
    graph=case.get('recipe_graph',{})
    def rec(oid,seen=()):
        if oid not in graph:return 'leaf'
        if oid in seen:return 'cycle'
        r=graph[oid]
        return ['craft',len(r['dependencies']),sorted([[v,rec(k,seen+(oid,))] for k,v in r['ingredients'].items()],key=json.dumps)]
    return json.dumps(rec(case['goal'].get('object_id')),sort_keys=True)


def main():
    new=json.loads(Path('results/sequence/dataset/cases.json').read_text())
    old=json.loads(Path('results/v3/dataset/cases.json').read_text())
    old_shapes={shape(c) for c in old if c.get('recipe_graph')};old_ids={c['goal'].get('object_id') for c in old}
    rows=[{'id':c['id'],'target_id':c['goal']['object_id'],'target_id_seen_in_other_old_game':c['goal']['object_id'] in old_ids,
        'coarse_recipe_tree_seen':shape(c) in old_shapes,'shape':shape(c)} for c in new if c['kind']=='craft']
    atomic_json('results/sequence/novelty_audit.json',{'new_craft_families':len(rows),
        'target_ids_also_in_old_worlds':sum(x['target_id_seen_in_other_old_game'] for x in rows),
        'coarse_recipe_trees_overlapping_old':sum(x['coarse_recipe_tree_seen'] for x in rows),
        'new_source_games':sorted({c['game'] for c in new}),
        'scope':'Original game worlds/initial states held out, NOT guaranteed unseen action schemas or abstract recipe mechanisms. Tree abstraction ignores object identity and shared-leaf identity; station count and ingredient quantities preserved. We did not rename objects or change official recipes.',
        'rows':rows})


if __name__=='__main__':main()
