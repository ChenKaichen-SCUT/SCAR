from pathlib import Path
import gzip
import json
from scar_stage24.common import read,write,sha,rows,gzwrite,offline,ROOT,ENGINE,ENGINE_COMMIT,MODEL,AGENT_ID,MAX_STEPS

RESULTS=ROOT/'results/stage28'
REPORTS=ROOT/'reports/stage28'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage28_runtime')
PARENT=ROOT/'results/stage25/runs/remnant__s42__AGC-v2'
CASES={
 'parent_a031':'Have a lockpick tool held in hand before continuing the original objective.',
 'parent_a054':'Have sufficient free hand space for iron_bar before continuing the original objective.',
 'parent_a060':'Have access to a workbench for crafting wood_plank before continuing the original objective.',
 'parent_a113':'Have sufficient free hand space for wooden_rod before continuing the original objective.',
 'parent_a136':'Have a writing tool held in hand before continuing the original objective.',
 'parent_a235':'Have sufficient necessary ingredients for crafting torch before continuing the original objective.',
 'parent_a270':'Have sufficient free space in small_satchel_0 for cloth before continuing the original objective.',
 'oracle032_a256':'Have access to a furnace for crafting glass_shard before continuing the original objective.',
 'oracle037_a122':'Have access to a workbench for crafting lockpick before continuing the original objective.',
 'oracle079_a165':'Have sufficient necessary ingredients for crafting star_metal_sword before continuing the original objective.',
}

def samples():return rows(ROOT/'results/stage27/failure_database.jsonl.gz')
def selected():return {s['id']:s for s in samples() if s['id'] in CASES}
def suffix(sample):return [r for r in rows(ROOT/sample['source_trajectory']) if r['step']>sample['step']]
def intervention(ident,goal):
    return '\n\nTemporary recovery objective:\n'+CASES[ident]+'\nOriginal objective to resume after recovery:\n'+goal+'\n'

def check_freeze(light=False):
    f=read(RESULTS/'freeze.json')
    for n,h in f['files'].items():
        if not light or n.startswith('scar_stage28/') or n=='results/stage28/checkpoint_manifest.json':assert sha(ROOT/n)==h,n
    if not light:
        for n,h in f['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(f['files']),engine_files=len(f['engine_files']))
