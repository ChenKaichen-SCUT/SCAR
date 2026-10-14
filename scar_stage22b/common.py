import copy
import gzip
import hashlib
import json
import socket
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results/stage22b'
REPORTS=ROOT/'reports/stage22b'
ENGINE=Path('/mnt/Space0/scar_dependencies/agentodyssey_stage22')
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage22b_runtime')
METHODS=('Stage18-Fixed','ShortTermMemoryAgent','LongContextAgent')
AGENT='agent_adam_davis'

def read(p):return json.loads(Path(p).read_text())
def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(s) for s in f]
def write(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def gzwrite(p,data):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt',encoding='utf-8') as f:
        for r in data:f.write(json.dumps(r,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(method):return ROOT/'results/stage22/runs'/f'mark__{method}'
def forbid_network():
    def deny(*a,**k):raise RuntimeError('Stage22-B forbids network and model calls')
    socket.create_connection=socket.socket.connect=socket.socket.connect_ex=deny
def check_freeze():
    p=read(RESULTS/'protocol.json')
    assert all(sha(ROOT/n)==h for n,h in p['prior_files'].items()),'Prior stage file changed'
    engine=read(ROOT/'results/stage22/freeze.json')['engine_files']
    assert all(sha(ENGINE/n)==h for n,h in engine.items()),'Official environment changed'
    return dict(prior_files_unchanged=len(p['prior_files']),official_files_unchanged=len(engine))
def table(headers,records):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
      ['| '+' | '.join(str(x).replace('|','\\|').replace('\n',' / ') for x in row)+' |' for row in records])

def internal(agent,method):
    if method=='LongContextAgent':
        return dict(kind='full_text_history',memory=agent.memory.get_all_memory(),
                    explicit_goal_field=None,goal_note='No separate structured goal; model reasoning is a declaration, not a hidden state readout.')
    value=dict(kind='STM5',memory=list(agent.short_term_memory),memory_size=agent.short_term_memory_size)
    if method=='Stage18-Fixed':
        value.update(controller=agent.controller.to_dict(),facts=agent.facts.to_dict(),
                     explicit_goal_field=agent.controller.target)
    else:value['explicit_goal_field']=None
    return copy.deepcopy(value)
