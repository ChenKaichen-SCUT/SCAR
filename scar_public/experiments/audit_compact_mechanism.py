import argparse,gzip,hashlib,json
from collections import Counter
from pathlib import Path
from scar_public.continuation import ContinuationMemory
parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
root=parser.parse_args().root
assert (root/'pipeline_complete.json').exists()
report=[]
for block in sorted((root/'evaluation').iterdir()):
    repair_hashes=set()
    for f in (block/'main/api').glob('*.request.json.gz'):
        with gzip.open(f,'rt') as stream:p=json.load(stream)
        msgs=p['messages']
        if len(msgs)>=2 and '\nReconsideration options:\n' in msgs[1].get('content',''):
            repair_hashes.add(hashlib.sha256((msgs[0]['content']+'\0'+msgs[1]['content']).encode()).hexdigest())
    for phase in ('main','scheduled'):
        calls=[json.loads(l) for l in (block/phase/'calls.jsonl').read_text().splitlines() if l]
        for arm in ('continuation_generic','checked','sentry','continuation_scheduled'):
            folder=block/phase/arm/'trace'
            if not folder.exists():continue
            counts=Counter();kinds=Counter();reasons=Counter();queries=[]
            rows=[json.loads(f.read_text()) for f in sorted(folder.glob('*.json'))]
            public_memory=ContinuationMemory();progress_counts=Counter();progress_examples=[];plateau_examples=[]
            def record_progress():
                o=public_memory.last_outcome
                if not o:return
                progress_counts['observed_transitions']+=1
                for field in ('progress','resource_change','discovery'):
                    progress_counts[field]+=bool(o[field])
                progress_counts['new_public_text']+=bool(o['new_facts'])
                if o['progress'] and len(progress_examples)<12 and o['action'].startswith('enter '):
                    progress_examples.append(o)
                index=o['step']
                if o['progress'] and o['action'].startswith('enter ') and index>=26:
                    window=rows[index-26:index]
                    if len({r['scores']['quest'] for r in window})==1:
                        progress_counts['movement_resets_during_25_action_quest_plateau']+=1
                        if len(plateau_examples)<8:plateau_examples.append(o)
            for row in rows:
                event=json.loads(row['response']).get('continuation',{})
                public_memory.observe(row['observation'],row['step']-1);record_progress()
                public_memory.commit(row['action'],'diagnostic-only')
                counts['actions']+=1
                if event.get('trigger'):
                    counts['triggered_proposals']+=1;kinds[event['trigger']['kind']]+=1
                    if 'proposal' not in event:reasons[event.get('reason','COOLDOWN_ALREADY_OFFERED')]+=1
                if 'proposal' in event:
                    counts['repair_queries']+=1;queries.append(dict(step=row['step'],original=event['original'],
                        executed=row['action'],changed=event['changed'],trigger=event['trigger']['kind'],
                        reason=event.get('reason'),rejected=event.get('rejected',[])))
                    counts['gate_changed_repair_proposal']+=row['action']!=event['proposal']['action']
                counts['changed_original_action']+=event.get('changed',False)
            public_memory.observe(rows[-1]['next_observation'],rows[-1]['step']);record_progress()
            if arm.startswith('continuation_'):
                checkpoint=block/phase/arm/'checkpoints'/f"{rows[-1]['step']:04d}"/'continuation.json'
                saved=json.loads(checkpoint.read_text())
                assert saved['epoch']==public_memory.epoch
                assert set(saved['facts'])==public_memory.facts
            repair_calls=[c for c in calls if c['arm']==arm and c['prompt_sha256'] in repair_hashes]
            assert len(repair_calls)==counts['repair_queries'],(block.name,arm,len(repair_calls),counts['repair_queries'])
            report.append(dict(game=block.name,arm=arm,counts=dict(counts),trigger_kinds=dict(kinds),
                trigger_without_query_reasons=dict(reasons),events=queries,
                public_progress_audit=dict(counts=dict(progress_counts),first_movement_examples=progress_examples,
                    plateau_examples=plateau_examples,
                    qualification='Post-hoc descriptive audit. A score plateau does not prove an action is useless; within each rule examples are chronological.'),
                repair_logical_input_tokens=sum(c['input_tokens'] for c in repair_calls),
                repair_logical_output_tokens=sum(c['output_tokens'] for c in repair_calls),
                token_qualification='Logical final valid responses; JSON-format retries charged in total API ledger, not counted here'))
(root/'mechanism_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps([{k:v for k,v in r.items() if k!='events'} for r in report],indent=2))
