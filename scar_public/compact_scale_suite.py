"""New author filenames at larger sizes, selected before solver outcomes.

Cube 13 has 2197 worlds and intentionally exceeds the declared 2048 model cap;
retain it in the denominator as unsupported, rather than silently sampling.
These are related generator families, not independent statistical draws.
"""
from scar_public.label_scale_suite import load, source_text


def configurations():
    return [dict(id=f'compact_scale_{family}_{n}_{overlay}', family=family, n=n,
        overlay=overlay, horizon=60, source='lug_author_archive', cohort='new_filename_scale')
        for family, sizes in (('cubecenter', (11, 13)), ('btc', (40, 60)))
        for n in sizes for overlay in ('original', 'a16s1')]


def provenance(cache, config):
    return source_text(cache, config)[2]
