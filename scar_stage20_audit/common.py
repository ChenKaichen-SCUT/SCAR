import copy
import gzip
import json
import os
from pathlib import Path
import socket

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'results/stage20'
RESULTS=ROOT/'results/stage20_audit'
REPORTS=ROOT/'reports/stage20_audit'
RUNTIME=ROOT/'runtime/stage20_audit'
BASE='a034a69756432daebd16114854d8d266ff90a2d0'
NETWORK_ATTEMPTS=[]


def deny_network():
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    def blocked(*args,**kwargs):
        NETWORK_ATTEMPTS.append('blocked_network_attempt')
        raise RuntimeError('Stage20 audit: all network/model/embedding calls prohibited')
    socket.create_connection=socket.socket.connect=socket.socket.connect_ex=socket.socket.sendto=blocked
    return blocked


def load(p):return json.loads(Path(p).read_text())
def write(p,value):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def read_gzip(p):
    with gzip.open(p,'rt') as f:return [json.loads(s) for s in f]
def gzip_rows(p,rows):
    with Path(p).open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as f:
            for row in rows:f.write((json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n').encode())
def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def folder(tid):return SOURCE/'runs'/f'{tid}__SCAR20'
def controller(state):
    from scar_stage20.controller import Controller20
    return Controller20.from_dict(copy.deepcopy(state))
