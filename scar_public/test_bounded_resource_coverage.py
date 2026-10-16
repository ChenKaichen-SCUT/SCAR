from itertools import product
from scar_public.test_symbolic_coverage import task
from scar_public.demand_coverage import DemandCoverage
from scar_public.bounded_resource_coverage import BoundedResourceCoverage


def test_exact_capacity_equality_without_work_cap():
    for projection in ((),('flag',),('flag','done')):
        t=task((6,4),{'make':(2,0),'sense':(0,1),'flag':(1,0)},projection)
        for mode in ('counts','lineage','matching'):
            original=DemandCoverage(t,mode,None)
            bounded=BoundedResourceCoverage(t,mode,None)
            for resources in product(range(7),range(5)):
                for values in product((False,True),repeat=len(t.projection)):
                    key=resources,sum(1<<i for i,b in zip(t.projection,values) if b)
                    for h in range(4):
                        assert original.capacity(key,h)==bounded.capacity(key,h)
                        for mask in range(1<<len(t.models)):
                            assert original.relational_capacity(key,mask,h)==bounded.relational_capacity(key,mask,h)
