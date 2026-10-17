"""Chronological offline audit; never imports future observations into a review."""
import argparse,json,tarfile
from collections import Counter
from pathlib import Path
from scar_public.intent_repair import IntentMemory,IntentController

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    result=[]
    with tarfile.open(a.archive) as archive:
        for game in ('mark','metropolis','remnant'):
            memory=IntentMemory();c=IntentController(memory);c.intervention_mode='observe'
            names=sorted(n for n in archive.getnames() if '/full_clock/' in n and '/'+game+'/trace/' in n)
            rows=[]
            for n in names:
                r=json.load(archive.extractfile(n));parsed=json.loads(r['response']);step=r['step']-1
                memory.prompt(r['observation']);c.prepare_decision(r['observation'],step)
                review=c.assess(parsed,step,'recorded_executed_proposal')
                if review['intent']['target']:rows.append(review)
                memory.update(parsed,r['observation'],step)
            result.append(dict(game=game,source='V12 recorded execution; audit only, not actual interventions',
                counts=dict(Counter(r['status'] for r in rows)),reviews=rows,
                would_intervene=[r for r in rows if r['would_intervene']],npc_tasks=memory.intent_tasks))
    a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps([dict(game=r['game'],counts=r['counts'],would_intervene_steps=[x['step']+1 for x in r['would_intervene']]) for r in result]))

if __name__=='__main__':main()
