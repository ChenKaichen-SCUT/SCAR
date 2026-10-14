import datetime
import subprocess
from .common import *

def main():
    assert not (RESULTS/'freeze.json').exists()
    assert read(RESULTS/'checkpoint_manifest.json')['passed'] and read(RESULTS/'smoke.json')['passed']
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT,text=True).split('\0')
    files={n:sha(ROOT/n) for n in names if n and (ROOT/n).is_file()}
    for folder in [ROOT/'scar_stage26',REPORTS,RESULTS]:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[str(p.relative_to(ROOT))]=sha(p)
    engine=read(ROOT/'results/stage25/freeze.json')['engine_files']
    assert all(sha(ENGINE/n)==h for n,h in engine.items())
    write(RESULTS/'freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        files=files,engine_files=engine,engine_commit=ENGINE_COMMIT,instruction_sha256=sha(ROOT.parent/'指引文件/指引26.md'),
        cases=CASES,old_files_modified=[],new_model_calls_before_freeze=0))
    print(json.dumps(dict(frozen_project_files=len(files),engine_files=len(engine),new_model_calls=0)))

if __name__=='__main__':main()
