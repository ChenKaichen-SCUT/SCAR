import subprocess
from pathlib import Path
with Path('/root/scar_effect_v4_20261018/replay_queue.log').open('w') as log:
    p=subprocess.Popen(['/root/scar_research_20261015/venv/bin/python','/root/queue_effect_replays_v4.py'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(p.pid)
