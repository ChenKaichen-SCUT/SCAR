import datetime
import subprocess
from .common import *

def main():
    assert not (RESULTS/'freeze.json').exists()
    assert read(RESULTS/'preparation.json')['passed'] and read(RESULTS/'smoke.json')['passed']
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT,text=True).split('\0')
    files={n:sha(ROOT/n) for n in names if n and (ROOT/n).is_file()}
    for folder in [ROOT/'scar_stage27',RESULTS,REPORTS]:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[str(p.relative_to(ROOT))]=sha(p)
    engine=read(ROOT/'results/stage26/freeze.json')['engine_files']
    assert all(sha(ENGINE/n)==h for n,h in engine.items())
    write(RESULTS/'freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files=files,engine_files=engine,model=MODEL,new_model_calls_before_freeze=0))

if __name__=='__main__':main()
