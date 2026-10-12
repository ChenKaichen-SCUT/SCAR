"""Provenance-gated public recipe calibration. No world, case, goal or oracle.

Only native observation feedback with an inspection/acquisition disclosure frame
or an actual craft missing-station response can assert facts. Similar prose and
model guesses are never promoted. This module is not installed into frozen S1.
"""
import copy
from decimal import Decimal
import re
from scar.agents.scar.state import feedback_text
from scar.io import digest
from scar_v3.state import parse_action

NAME=r'[A-Za-z_][A-Za-z0-9_-]*'
NUMBER=r'\d+(?:\.\d+)?'


def extract(observation,source_action,*,source_kind='native_observation',cutoff=None):
    if source_kind!='native_observation':return [],[{'reason':'untrusted_non_native_source'}]
    step=int(observation['step'])
    if cutoff is not None and step>cutoff:raise ValueError('future observation exceeds causal cutoff')
    text=observation['text']
    # Synthetic boundary fixtures may supply a native feedback block directly;
    # callers must attest provenance. Actual source ingestion asserts full rows.
    feedback=feedback_text(text);p=parse_action(source_action or '')
    lines=feedback.splitlines();facts=[];ambiguous=[]
    inspected=bool(p.verb=='inspect' and re.search(r'^I inspected '+NAME+r':',feedback,re.M))
    for line in lines:
        body=None;form=None
        if line.startswith('It can be used to craft:') and inspected:
            body=line.split('It can be used to craft:',1)[1].strip();form='inspection_names'
        acquired=re.fullmatch(r'I have acquired a new item: ('+NAME+r')\. It can be used to craft: (.*)',line)
        if acquired:
            body=acquired[2].strip();form='acquisition_quantities'
        if body is not None and body.rstrip('.')!='None':
            # Verify the complete list grammar, not just arbitrary matching
            # substrings. A malformed entry is retained as ambiguous evidence.
            matches=list(re.finditer(r'('+NAME+r') \(([^)]+)\)',body))
            cursor=0; gaps=[]
            for match in matches:
                if body[cursor:match.start()].strip(' ,.'):gaps.append(body[cursor:match.start()])
                cursor=match.end()
            if body[cursor:].strip(' ,.'):gaps.append(body[cursor:])
            if gaps:
                ambiguous.append({'reason':'unparsed_recipe_list_text','raw_evidence':line,'observed_step':step})
                continue
            cursor=0
            for m in matches:
                gap=body[cursor:m.start()].strip(' ,.')
                if gap:ambiguous.append({'reason':'unparsed_recipe_list_text','raw_evidence':gap,'observed_step':step})
                product=m[1];inside=m[2];quantities=None
                if inside.startswith('made of '):
                    ingredients=[x.strip() for x in inside[8:].split(',')]
                    valid=bool(ingredients) and all(re.fullmatch(NAME,n) for n in ingredients)
                else:
                    numbers=[re.fullmatch('('+NUMBER+r') ('+NAME+')',x.strip()) for x in inside.split(',')]
                    valid=bool(numbers) and all(numbers)
                    ingredients=[x[2] for x in numbers] if valid else []
                    if valid:
                        quantities={x[2]:float(Decimal(x[1])) for x in numbers}
                        valid=all(v>0 for v in quantities.values()) and len(quantities)==len(numbers)
                if valid:
                    facts.append({'product':product,'ingredients':ingredients,'quantities':quantities,'stations':None,
                        'source_action':source_action,'observed_step':step,'raw_evidence':line,'certainty':'EXPLICIT_RELATION',
                        'format':form,'station_completeness':'UNKNOWN'})
                else:ambiguous.append({'reason':'ambiguous_recipe_entry','raw_evidence':m[0],'observed_step':step})
                cursor=m.end()
            if body[cursor:].strip(' ,.'):ambiguous.append({'reason':'unparsed_recipe_list_tail','raw_evidence':body[cursor:],'observed_step':step})
        station=re.fullmatch(r'Cannot craft ('+NAME+r')\. Missing necessary (.+?) in the current area\.',line)
        if station and p.verb=='craft' and p.target==station[1]:
            names=[n.strip() for n in station[2].split(',')]
            if all(re.fullmatch(NAME,n) for n in names):
                facts.append({'product':station[1],'ingredients':None,'quantities':None,'stations':names,
                    'source_action':source_action,'observed_step':step,'raw_evidence':line,'certainty':'PARTIAL_STATION_REQUIREMENT',
                    'format':'craft_missing_stations','station_completeness':'known_required_subset'})
    return facts,ambiguous


class Knowledge:
    def __init__(self):self.facts={};self.events=[];self.ambiguous=[];self.seen=set()
    def clone(self):return copy.deepcopy(self)
    def observe(self,obs,action,*,source_kind='native_observation',cutoff=None,source=None):
        if cutoff is not None and int(obs['step'])>cutoff:raise ValueError('future observation exceeds causal cutoff')
        signature=digest([obs['step'],obs['text']])
        if signature in self.seen:return {'new_relations':[],'quantity_updates':[],'station_updates':[],'repeated_relations':[],'duplicate_observation':True,'events':[]}
        extracted,ambiguous=extract(obs,action,source_kind=source_kind,cutoff=cutoff)
        if source_kind!='native_observation':return {'new_relations':[],'quantity_updates':[],'station_updates':[],'repeated_relations':[],'duplicate_observation':False,'events':[],'untrusted':True}
        self.seen.add(signature);self.ambiguous.extend(dict(a,source=source) for a in ambiguous)
        delta={'new_relations':[],'quantity_updates':[],'station_updates':[],'repeated_relations':[],'duplicate_observation':False,'events':[]}
        for e in extracted:
            name=e['product'];old=self.facts.get(name)
            if old is None:
                old={'product':name,'ingredients':None,'quantities':None,'stations':None,'source_action':e['source_action'],
                    'observed_step':e['observed_step'],'first_relation_step':None,'first_quantity_step':None,
                    'raw_evidence':e['raw_evidence'],'certainty':e['certainty'],'station_completeness':'UNKNOWN','evidence_ids':[]}
                self.facts[name]=old
            changes=[];conflict=False
            if e['ingredients'] is not None:
                if old['ingredients'] is None:
                    old['ingredients']=sorted(e['ingredients']);old['first_relation_step']=e['observed_step']
                    delta['new_relations'].append(name);changes.append('new_relation')
                elif set(old['ingredients'])!=set(e['ingredients']):conflict=True
                else:delta['repeated_relations'].append(name)
            if e['quantities'] is not None and not conflict:
                if old['quantities'] is None:
                    old['quantities']=e['quantities'];old['first_quantity_step']=e['observed_step']
                    delta['quantity_updates'].append(name);changes.append('explicit_quantities_added')
                elif old['quantities']!=e['quantities']:conflict=True
            if e['stations']:
                new=set(e['stations'])-set(old['stations'] or [])
                if new:
                    old['stations']=sorted(set(old['stations'] or [])|new);old['station_completeness']='known_required_subset'
                    delta['station_updates'].append(name);changes.append('required_station_added')
            if conflict:
                old['certainty']='AMBIGUOUS_CONFLICT';changes.append('conflict_not_overwritten')
            elif old['certainty']!='AMBIGUOUS_CONFLICT':old['certainty']='EXPLICIT_RELATION' if old['ingredients'] else 'PARTIAL_STATION_REQUIREMENT'
            event=dict(e,changes=changes or ['repeated_disclosure'],source=source,conflict=conflict)
            event['event_id']='k14_'+digest([source,e])[:16];old['evidence_ids'].append(event['event_id'])
            self.events.append(event);delta['events'].append(event)
        for k in ['new_relations','quantity_updates','station_updates','repeated_relations']:delta[k]=sorted(set(delta[k]))
        return delta
    def relations(self):return {n:copy.deepcopy(f) for n,f in self.facts.items() if f['ingredients'] and f['certainty']!='AMBIGUOUS_CONFLICT'}
    def view(self):return copy.deepcopy(self.facts)
    @classmethod
    def from_dict(cls,data):
        obj=cls();obj.facts=copy.deepcopy(data['facts']);obj.events=copy.deepcopy(data.get('events',[]));obj.ambiguous=copy.deepcopy(data.get('ambiguous',[]));obj.seen=set(data.get('seen',[]));return obj
    def to_dict(self):return {'facts':self.view(),'events':copy.deepcopy(self.events),'ambiguous':copy.deepcopy(self.ambiguous),'seen':sorted(self.seen)}
