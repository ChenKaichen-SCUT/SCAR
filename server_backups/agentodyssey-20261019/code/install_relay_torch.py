import subprocess,pathlib
R=pathlib.Path('/root/agentodyssey-benchmark-20261018')
p=subprocess.run([str(R/'.venv/bin/python'),'-m','pip','install','--no-cache-dir',str(R/'torch-2.10.0+cpu-cp310-cp310-manylinux_2_28_x86_64.whl'),'--index-url','https://mirrors.huaweicloud.com/repository/pypi/simple'],check=True)
(R/'base_ready.flag').write_text('ok')
