"""Extract auditable development regressions from an existing public archive."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from scar.io import atomic_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    report=dict(archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
                index_convention='one-based actions; historical branch step+1',blocks={})
    selected={};hashes={};manifest=None
    prefixes=[f'{phase}/branches/{block}/{arm}/trace/'
              for phase,arm in [('revision2','off'),('generic_control','repair')]
              for block in ('mark_r0','metropolis_r1')]
    audit_names=[f'generic_control/branches/{b}/environment_audit.json' for b in ('mark_r0','metropolis_r1')]
    # Stream once: random seeking inside a large gzip archive is quadratic.
    with tarfile.open(a.archive,'r|gz') as tar:
        for member in tar:
            name=member.name
            if name=='manifest.json':manifest=json.load(tar.extractfile(member))
            elif any(name.startswith(prefix) for prefix in prefixes) or name in audit_names:
                data=tar.extractfile(member).read();hashes[name]=hashlib.sha256(data).hexdigest()
                selected[name]=json.loads(data)
    assert manifest is not None
    if selected:
        def read(name):
            assert hashes[name]==manifest[name]
            return selected[name]
        for block in ('mark_r0','metropolis_r1'):
            b={};report['blocks'][block]=b
            for label,prefix in [('off',f'revision2/branches/{block}/off/trace/'),
                                 ('compact',f'generic_control/branches/{block}/repair/trace/')]:
                rows=[read(n) for n in sorted(manifest) if n.startswith(prefix)]
                events=[];milestones=[];last=None
                for r in rows:
                    if r['scores']['quest']!=last:
                        milestones.append(dict(action_index=r['step']+1,quest=r['scores']['quest'],action=r['action']))
                        last=r['scores']['quest']
                    e=r['response'].get('continuation',{})
                    if 'proposal' in e:
                        events.append(dict(action_index=r['step']+1,original=e['original'],executed=r['action'],
                            changed=e['changed'],trigger=e['trigger']['kind'],goals=e['packet']['goals'],
                            selection=e.get('rejected'),proposal=e['proposal'],
                            observation=r['observation'],feedback=r['next_observation']))
                b[label]=dict(final_scores=rows[-1]['scores'],milestones=milestones,events=events)
            b['one_step_diagnostics']=read(f'generic_control/branches/{block}/environment_audit.json')['same_state_diagnostics']
            for e in b['one_step_diagnostics']:e['action_index']=e.pop('step')+1
    atomic_json(a.out,report)


if __name__=='__main__':main()
