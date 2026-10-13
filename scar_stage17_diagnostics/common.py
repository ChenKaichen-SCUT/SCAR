import hashlib
import json
import socket
import subprocess
from pathlib import Path
from scar_stage17.common import ROOT, RESULTS, load, write, read_gzip, gzip_rows, sha, METHODS

OUT = RESULTS / 'diagnostics'
OUT.mkdir(exist_ok=True)

def deny_network():
    def denied(*args, **kwargs):
        raise RuntimeError('Stage17 diagnostics prohibits network/model calls')
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied

def baseline():
    path = OUT / 'input_manifest.json'
    if not path.exists():
        files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
        write(path, dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
                        files={p:sha(ROOT/p) for p in files if p and not p.startswith('scar_stage17_diagnostics/') and '/diagnostics/' not in p}))
    data=load(path)
    assert all(sha(ROOT/p)==h for p,h in data['files'].items()), 'Frozen input modified'
    return len(data['files'])

def run_dir(t,m):
    return RESULTS/'runs'/f"{t['task_id']}__{m}"

def eid(t,m,step):
    return f"{t['task_id']}__{m}:a{step:03d}"

def norm(s):
    return ' '.join(s.split())

def coverage(facts, graph):
    # Hidden rules label the recipe scope ONLY. Do not read hidden quantities or
    # station lists to complete an agent's epistemic state.
    out={k:[] for k in ('relation','quantity','station_requirement_disclosed','full_explicitly_confirmed')}
    for rule in graph.values():
        n=rule['name'];f=facts.get(n,{})
        rel=bool(f.get('ingredients')) and f.get('certainty')!='AMBIGUOUS_CONFLICT'
        qty=rel and isinstance(f.get('quantities'),dict) and set(f['quantities'])==set(f['ingredients'])
        sta=bool(f.get('stations'))
        if rel:out['relation'].append(n)
        if qty:out['quantity'].append(n)
        if sta:out['station_requirement_disclosed'].append(n)
        if qty and f.get('station_completeness')=='explicit_complete':out['full_explicitly_confirmed'].append(n)
    return {k:sorted(v) for k,v in out.items()}
