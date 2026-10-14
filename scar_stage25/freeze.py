"""Pre-run protocol and immutable source/state manifest."""
import datetime
import subprocess
from .common import *


def main():
    assert not (RESULTS/'freeze.json').exists()
    assert all(read(RESULTS/n)['passed'] for n in ['preflight.json','smoke.json','initial_receipt.json'])
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    old_names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT,text=True).split('\0')
    files={n:sha(ROOT/n) for n in old_names if n and (ROOT/n).is_file()}
    for folder in ['agents/agc_v2','scar_stage25','reports/stage25','results/stage25']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[str(p.relative_to(ROOT))]=sha(p)
    engine=read(ROOT/'results/stage22/freeze.json')['engine_files']
    assert all(sha(ENGINE/n)==h for n,h in engine.items())
    write(RESULTS/'freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=source_commit,
        files=files,engine_files=engine,engine_commit=ENGINE_COMMIT,old_files_modified=[],
        instruction_sha256=sha(ROOT.parent/'指引文件/指引25.md')))
    print(json.dumps(dict(source_commit=source_commit,frozen_project_files=len(files),engine_files=len(engine),calls_before_freeze=0)))

if __name__=='__main__':main()
