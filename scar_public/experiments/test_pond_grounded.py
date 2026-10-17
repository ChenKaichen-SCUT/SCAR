from itertools import product
import pytest
from scar_public.compiled_task import CompiledTask
from scar_public.finite_planner import State
from scar_public.experiments.pond_grounded import export,replay_sequence
from scar_public.bounded_resource_coverage import BoundedResourceCoverage

def test_grounded_adapter_roundtrip_and_replay():
    d='(define (domain d) (:predicates (h) (done)) (:action left :parameters () :effect (when (h) (done))) (:action right :parameters () :effect (when (not (h)) (done))))'
    p='(define (problem p) (:domain d) (:init (unknown (h))) (:goal (done)))'
    t=CompiledTask(d,p);d,p,mapping=export(t);u=CompiledTask(d,p)
    positions={int(name[0][1:]):i for i,name in enumerate(u.atom_names)}
    def convert(bits):return sum(1<<positions[i] for i in range(len(t.atom_names)) if bits&(1<<i))
    assert {convert(b) for b in t.initial_bits}==set(u.initial_bits)
    for bits in range(1<<len(t.atom_names)):
        for token,action in mapping.items():
            a,_=t.step(State((bits,True),()),action)
            b,_=u.step(State((convert(bits),True),()),token)
            assert (convert(a.symbols[0]),a.symbols[1])==b.symbols
    assert replay_sequence(t,mapping,['a0','a1'])==2
    with pytest.raises(ValueError):replay_sequence(t,mapping,[])
    with pytest.raises(ValueError):replay_sequence(t,mapping,['a0'])

def test_homogeneous_label_collapse_for_all_masks_and_small_keys():
    d='''(define (domain d) (:predicates (h0) (h1) (h2) (start) (stage) (done))
    (:action prepare :parameters () :precondition (start)
      :effect (and (not (start)) (stage) (not (h0)) (not (h1)) (not (h2))))
    (:action finish :parameters () :precondition (stage) :effect (when (h0) (done))))'''
    p='(define (problem p) (:domain d) (:init (start) (oneof (h0) (h1) (h2))) (:goal (done)))'
    t=CompiledTask(d,p,resources=(2,),resource_costs={'prepare':(1,),'finish':(1,)},
                   projection_predicates=('start','stage'))
    assert len(set(t.static_bits))==1
    bounds={mode:BoundedResourceCoverage(t,mode,10000) for mode in ('counts','lineage','matching')}
    for values in product((0,1),repeat=len(t.projection)):
        z=sum(v<<i for i,v in zip(t.projection,values))
        for resource in range(3):
            for depth in range(4):
                q=((resource,),z);c=bounds['counts'].capacity(q,depth)
                assert c in (0,3)
                for mask in range(8):
                    for mode in ('lineage','matching'):
                        assert bounds[mode].relational_capacity(q,mask,depth)==min(mask.bit_count(),c)
