import datetime,subprocess
from .common import *
def main():
    assert not (RESULTS/'freeze.json').exists()
    assert read(RESULTS/'preparation.json')['passed'] and read(RESULTS/'smoke.json')['passed']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    files={n:sha(ROOT/n) for n in names if n and (ROOT/n).is_file()}
    for folder in [ROOT/'agents/saer',ROOT/'scar_stage32',RESULTS,REPORTS]:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[str(p.relative_to(ROOT))]=sha(p)
    engine=read(ROOT/'results/stage31/freeze.json')['engine_files'];assert all(sha(ENGINE/n)==h for n,h in engine.items())
    write(RESULTS/'freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=BASE,files=files,engine_files=engine,model=MODEL,
        instruction_sha256=sha(ROOT.parent/'指引文件/指引32.md'),seeds=SEEDS,offline_samples=77,offline_new_calls_planned=154,
        new_model_calls_before_freeze=0,online_runs=3,max_environment_actions_each=300,risk_filter=False,policy_changes_after_offline_forbidden=True))
    print(json.dumps(dict(files=len(files),engine_files=len(engine))),flush=True)
if __name__=='__main__':main()
