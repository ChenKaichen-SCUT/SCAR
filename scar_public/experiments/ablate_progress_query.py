"""Cold-start comparison on a saved development query, including scalar costs."""
import argparse, json, platform
from pathlib import Path
from time import perf_counter
from scar_public.compact_progress import CompactProgress
from scar_public.factored_progress import FactoredProgress
from scar_public.study_reachable_labels import load
from scar_public.budgeted_planner import InferenceStop
from scar_public.symbolic_coverage import Unavailable


def main():
    p = argparse.ArgumentParser(); p.add_argument('cache', type=Path)
    p.add_argument('input', type=Path); p.add_argument('output', type=Path); a = p.parse_args()
    saved = json.loads(a.input.read_text())
    query = next(x for x in saved['probes'] if x.get('lineage', float('inf')) < x.get('candidates', 0))
    task, _ = load(a.cache, saved['config'])
    key = tuple(query['resources']), tuple(tuple(x) for x in query['groups'])
    rows = []
    for cls in (CompactProgress, FactoredProgress):
        start = perf_counter(); c = cls(task); c.deadline = start+10.
        row = dict(method=cls.__name__, candidates=query['candidates'], budget=query['budget'])
        try:
            row['scalar'] = c.value(key, query['budget'])
            counted = perf_counter(); row['scalar_seconds'] = counted-start
            row['lineage'] = c.value(key, query['budget'], True)
            row['relation_seconds'] = perf_counter()-counted
            row['status'] = 'completed'
        except (InferenceStop, Unavailable):
            row['status'] = 'interrupted'
        row.update(total_seconds=perf_counter()-start, statistics=c.stats); rows.append(row)
    a.output.write_text(json.dumps(dict(query=query, rows=rows, python=platform.python_version(),
        platform=platform.platform(), scope='Selected development query; no held-out or production-speed claim.'), indent=2))
    print(json.dumps([{k: v for k,v in r.items() if k != 'statistics'} for r in rows]))


if __name__ == '__main__':
    main()
