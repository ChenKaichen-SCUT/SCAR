"""P1 adapter; identical observation timing and summary to frozen Stage15.

The Stage14 parser is reused as the sole source of nominal recipe knowledge.
Batch samples stay in the frozen S1 auxiliary facts, not nominal recipes.
"""
import copy
from scar_sequence.public import ResourceTable
from scar_unknown17.facts import PublicFacts
from scar_stage14.knowledge import Knowledge


class PublicTable(ResourceTable):
    def __init__(self, knowledge=None, **kwargs):
        super().__init__(**copy.deepcopy(kwargs))
        self.knowledge=Knowledge.from_dict(knowledge) if knowledge else Knowledge()

    def sync(self):
        # Do not let the legacy parser or craft-to-inspection averages assert
        # nominal recipe weights. Conflicting relations cease to be actionable.
        self.recipes={n:{'ingredients':copy.deepcopy(f['ingredients'] or []),
            'quantities':copy.deepcopy(f['quantities']),
            **({'stations':copy.deepcopy(f['stations'])} if f['stations'] else {}),
            'step':f['observed_step'],'source':'native_public_disclosure',
            'first_relation_step':f['first_relation_step'],'first_quantity_step':f['first_quantity_step'],
            'evidence_ids':list(f['evidence_ids']), 'station_completeness':f['station_completeness']}
            for n,f in self.knowledge.facts.items() if f['certainty']!='AMBIGUOUS_CONFLICT'}

    def observe(self,obs,action=None):
        super().observe(obs,action)
        if action is not None:
            self.knowledge.observe(obs,action,cutoff=obs['step'],source={'action':action,'step':obs['step']})
        self.sync()
        return self

    def to_dict(self):
        return super().to_dict() | {'knowledge':self.knowledge.to_dict()}


class PublicFacts16(PublicFacts):
    def __init__(self):
        super().__init__(); self.table=PublicTable()

    def records(self,obs):
        records=super().records(obs)
        for row in records:
            if row['kind']=='recipe':
                fact=self.table.recipes[row['key']]
                row['value']['quantities']=copy.deepcopy(fact['quantities']) if fact['quantities'] is not None else 'UNKNOWN'
                row['scope']='explicit nominal public recipe; batch consumption UNKNOWN; stations are known required subset'
            elif row['kind']=='uncertainty':
                row['value']['unknown_quantity_rules']=[n for n in row['value']['unknown_quantity_rules'] if not self.table.recipes.get(n,{}).get('quantities')]
        return records

    @classmethod
    def from_dict(cls,data):
        data=copy.deepcopy(data)
        obj=cls();obj.__dict__.update(copy.deepcopy(data));obj.table=PublicTable(**data['table']);return obj
