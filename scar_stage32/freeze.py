import datetime,subprocess
from .common import *

def main():
    assert not (RESULTS/'freeze.json').exists();assert read(RESULTS/'smoke.json')['passed'];assert SEEDS==[42]
    source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    files={n:sha(ROOT/n) for n in names if n and (ROOT/n).is_file()}
    for folder in [ROOT/'agents/saer',ROOT/'scar_stage32',RESULTS,REPORTS]:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[str(p.relative_to(ROOT))]=sha(p)
    engine=read(ROOT/'results/stage31/freeze.json')['engine_files'];assert all(sha(ENGINE/n)==h for n,h in engine.items())
    write(RESULTS/'freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=source,files=files,engine_files=engine,model=MODEL,
        instruction_sha256=sha(ROOT.parent/'指引文件/指引32.md'),user_scope_override='One repaired seed42 run, fresh initial state, previous Stage32 records removed.',
        seeds=SEEDS,online_runs=1,max_environment_actions_each=300,new_model_calls_before_freeze=0,offline_paid_samples=0,risk_filter=False))
    print(json.dumps(dict(source_commit=source,files=len(files),engine_files=len(engine))),flush=True)

if __name__=='__main__':main()
