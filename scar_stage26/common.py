from pathlib import Path
import gzip
import json
from scar_stage24.common import read,write,sha,rows,gzwrite,offline,ROOT,ENGINE,ENGINE_COMMIT,MODEL,AGENT_ID,MAX_STEPS

RESULTS=ROOT/'results/stage26'
REPORTS=ROOT/'reports/stage26'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage26_runtime')
SOURCE=ROOT/'results/stage25/runs/remnant__s42__AGC-v2'
INITIAL=ROOT/'results/stage25/initial/remnant__s42__AGC-v2'

# Offline experiment interventions, never imported by an agent or prompt.
# Each choice uses only the observation/prefix at this checkpoint.
CASES={
    28:dict(action='pick up key',subtype='locked_exit',basis='Visible key and empty hands at hall; one acquisition, no route supplied.'),
    32:dict(action='pick up key',subtype='repeated_missing_tool',basis='The last public response says no lockpick held; key is visible and hands empty.'),
    37:dict(action='pick up key',subtype='object_not_held',basis='Same object as proposed equip, visibly on ground, not held.'),
    54:dict(action='enter hall',subtype='hand_capacity',basis='Carry existing iron_bar and light into a currently listed adjacent area; hall workbench was public at a28. No item discarded.'),
    60:dict(action='enter hall',subtype='missing_workbench',basis='Hall is currently adjacent and its workbench was publicly observed earlier. One move, no craft sequence supplied.'),
    79:dict(action='attack goblin_warrior_1',subtype='combat_blocks_exit',basis='The visible enemy is attacking in the immediately preceding observation; a single attack, no future combat plan.'),
    85:dict(action='equip small_bag_0',subtype='not_equippable',basis='Choose the other explicitly held object, a bag, as a single equip proposal. Native acceptance is checked offline.'),
    136:dict(action='drop cloth',subtype='missing_writing_tool',basis='Both hands occupied; dropping held cloth frees one slot while retaining light. The visible pen is not automatically collected.'),
    235:dict(action='inspect small_satchel_0',subtype='insufficient_ingredients',basis='Inspect the explicitly equipped container to expose its current contents; no recipe or quantities supplied.'),
    270:dict(action='equip small_satchel_0',subtype='container_capacity',basis='The container is currently held and nothing equipped. One equip action, without changing its contents.'),
}
def case_id(n):return f'remnant_a{n:03d}'
def check_freeze():
    d=read(RESULTS/'freeze.json')
    for n,h in d['files'].items():assert sha(ROOT/n)==h,n
    for n,h in d['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(d['files']),engine_files=len(d['engine_files']))
