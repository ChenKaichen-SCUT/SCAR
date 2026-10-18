"""Finish the active batch with prior completed caches; exits after dispatch."""
import json,subprocess,time
from pathlib import Path
root=Path('/root/scar_effect_v3_20261018');old=Path('/root/scar_effect_v2_20261018')
pending={'mark_r0','metropolis_r1','metropolis_7537'}
for _ in range(60):
    jobs=json.loads((root/'jobs.json').read_text())
    pending-=set(j['name'] for j in jobs)
    ready=sorted(n for n in pending if (old/'evaluation'/n/'result.json').exists())
    if ready:
        subprocess.run(['/root/scar_research_20261015/venv/bin/python','/root/launch_effect_games_v3.py',*ready],check=True)
        pending-=set(ready)
    if not pending:break
    time.sleep(30)
assert not pending,sorted(pending)
(root/'replay_queue_complete.json').write_text(json.dumps(dict(dispatched=True)))
