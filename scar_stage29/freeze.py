import datetime
import subprocess
from .common import *

def main():
    offline();assert not (RESULTS/'freeze.json').exists()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT,text=True).split('\0')
    files={n:sha(ROOT/n) for n in names if n and (ROOT/n).is_file()}
    for folder in [ROOT/'scar_stage29',REPORTS]:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[str(p.relative_to(ROOT))]=sha(p)
    engine=read(ROOT/'results/stage28/freeze.json')['engine_files']
    assert all(sha(ENGINE/n)==h for n,h in engine.items())
    write(RESULTS/'freeze.json',dict(base_commit=BASE,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        files=files,engine_files=engine,instruction_sha256=sha(ROOT.parent/'指引文件/指引29.md'),new_model_calls=0))
    print('Frozen',len(files),'project files and',len(engine),'engine files',flush=True)

if __name__=='__main__':main()
