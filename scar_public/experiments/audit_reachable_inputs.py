"""Structural duplicate audit; never calls a planner or reads source solutions."""
import argparse, json
from pathlib import Path
from hashlib import sha256
from scar_public.reachable_holdout import load, source, configurations
from scar_public.benchmark_suite import source_text, PROJECTIONS
from scar_public.compiled_task import CompiledTask


def signature(t):
    def expr(e):
        if type(e) is bool:
            return str(e)
        if type(e) is int:
            return ('+' if e > 0 else '-')+' '.join(t.atom_names[abs(e)-1])
        op, args = e
        return op+'('+','.join(sorted(expr(x) for x in args))+')'
    worlds = tuple(sorted(tuple(sorted(t.atom_names[i] for i in range(len(t.atom_names)) if b & (1 << i))) for b in t.initial_bits))
    actions = tuple(sorted((a.name, expr(a.pre), tuple(sorted((expr(g), expr(l)) for g, l in a.effects)),
        None if a.observation is None else expr(a.observation)) for a in t.actions.values()))
    return sha256(repr((worlds, expr(t.goal_expr), actions)).encode()).hexdigest()


def audit(cache):
    old = {}
    for n in (2, 4, 6, 8):
        d, p, _ = source_text(cache, 'rovers', f'pfile{n}')
        t = CompiledTask(d, p, projection_predicates=PROJECTIONS['rovers'], model_limit=2048)
        old[signature(t)] = f'cff_rovers_pfile{n}'
    rows = []
    for n in range(1, 7):
        c = dict(family='rovers', instance=f'pfile{n}', overlay='original')
        t, origin = load(cache, c); sig = signature(t)
        rows.append(dict(file=c['instance'], candidates=len(t.models), transition_signature=sig,
            duplicate_old=old.get(sig), selected=n in (2, 3, 5), origin=origin))
    assert [r['file'] for r in rows if r['duplicate_old']] == ['pfile4', 'pfile6']
    assert all(r['origin']['domain_declarations_match'] for r in rows)
    return dict(rows=rows, selection='Exclude single-world pfile1 and structurally identical pfile4/6, keep all remaining files. '
        'Signature equality is sufficient for these compiled tasks to agree, not a complete semantic-equivalence test. '
        'Initial audit preceded solver outcomes; this script reproduces the structural check.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('cache', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(audit(a.cache), indent=2))
