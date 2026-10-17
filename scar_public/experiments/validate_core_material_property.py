"""Exhaustive small oracle for the implemented material-witness property.

The oracle executes a returned schedule under each quantity profile, preserving
real stock. It checks effects independently of witness recursion. Capacity and
navigation are deliberately absent, matching the theorem's stated relaxation.
"""
from itertools import product
import json
import math
from types import SimpleNamespace

from scar_public.method_repair import joint_material_completion


def validate():
    recipes={'bar':dict(needs={'wood':.5,'ore':.5},quote='bar requires .5 wood and .5 ore'),
             'key':dict(needs={'bar':2},quote='key requires2 bar'),
             'shield':dict(needs={'bar':1,'wood':.5},quote='shield requires1 bar and .5 wood')}
    model=SimpleNamespace(recipes=recipes)
    cases=certificates=executions=0
    for counts in product(range(4),repeat=5):
        stock=dict(zip(('wood','ore','bar','key','shield'),counts))
        for goals in ([('key',1)],[('shield',1)],[('key',1),('shield',1)]):
            cases+=1
            witness=joint_material_completion(model,stock,goals)
            if witness['status']!='JOINT_MATERIAL_WITNESS':continue
            certificates+=1
            for modes in product(('exact','ceil_batch','ceil_per_output'),repeat=3):
                actual=dict(stock);profile=dict(zip(recipes,modes))
                for action in witness['schedule']:
                    name,q=action['output'],action['quantity']
                    for item,n in recipes[name]['needs'].items():
                        cost=q*n if profile[name]=='exact' else math.ceil(q*n) if profile[name]=='ceil_batch' else q*math.ceil(n)
                        assert actual[item]>=cost, (stock,goals,witness,profile)
                        actual[item]-=cost
                    actual[name]+=q
                assert all(actual[item]>=q for item,q in goals), (stock,goals,witness,profile,actual)
                executions+=1
    return dict(cases=cases,positive_material_witnesses=certificates,profile_executions=executions,
                violations=0,scope='Finite relaxed resource instances only, not full game feasibility or policy value')


if __name__=='__main__':print(json.dumps(validate(),indent=2))
