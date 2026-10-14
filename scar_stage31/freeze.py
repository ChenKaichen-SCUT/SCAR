import datetime
import subprocess
from .common import *

def main():
    assert not (RESULTS/'freeze.json').exists()
    for name in ['smoke.json','preparation.json','offline_native_validation.json']:assert read(RESULTS/name)['passed']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT,text=True).split('\0')
    files={n:sha(ROOT/n) for n in names if n and (ROOT/n).is_file()}
    for folder in [ROOT/'agents/rec_v1',ROOT/'scar_stage31',REPORTS,RESULTS]:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[str(p.relative_to(ROOT))]=sha(p)
    engine=read(ROOT/'results/stage30/freeze.json')['engine_files'];assert all(sha(ENGINE/n)==h for n,h in engine.items())
    write(RESULTS/'freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=BASE,
        files=files,engine_files=engine,model=MODEL,instruction_sha256=sha(ROOT.parent/'指引31.md'),cases=CASES,
        new_model_calls_before_freeze=0,max_rec_reconsiderations=2,new_online_jobs=5,max_new_actions=1406))
    print(json.dumps(dict(files=len(files),engine_files=len(engine))),flush=True)

if __name__=='__main__':main()
