"""Bounded deterministic summary of public evidence, never hidden recipes.

Consumption samples are observed deltas over craft + inspection, not timeless
stoichiometry. Native environment effects may contribute to those deltas.
"""
from collections import Counter
import copy
import json
import re
from scar_sequence.public import ResourceTable
from scar_v3.state import parse_action, PublicState


def carried_counts(table):
    if table.state.get('hands') is None or table.state.get('equipment') is None:return None
    count=Counter(table.state['hands'])+Counter(table.state['equipment'])
    for name,c in table.containers.items():
        if table.carried(name):
            if c['counts'] is None:return None
            count.update(c['counts'])
    return dict(count)


class PublicFacts:
    MAX_RECORDS=48
    MAX_CHARACTERS=6000

    def __init__(self):
        self.table=ResourceTable();self.effects=[];self.failures=[];self.pending=None
        self.produced={};self.target='';self.goal='';self.amount=1

    def set_goal(self,action,goal):
        self.target=parse_action(action).target;self.goal=goal
        m=re.search(r'at least (\d+)',goal);self.amount=int(m[1]) if m else 1

    def observe(self,before,action,after):
        self.table.observe(before);counts=carried_counts(self.table);p=parse_action(action)
        feedback=PublicState.observe(after).feedback
        # Evidence window is immediate craft followed only by inventory inspect.
        if self.pending and p.verb!='inspect':self.pending=None
        self.table.observe(after,action)
        if p.verb=='craft':
            m=re.search(r'successfully crafted (\d+)',feedback)
            if m:
                actual=int(m[1]);self.produced[p.target]=self.produced.get(p.target,0)+actual
                self.pending={'target':p.target,'requested':int(p.args[0]),'actual':actual,
                    'before_counts':counts,'source_step':after.get('step',0),'feedback':feedback,
                    'location':self.table.state.get('location')} if counts is not None else None
            elif 'Cannot ' in feedback:
                self.failures.append({'target':p.target,'action':action,'feedback':feedback,
                    'location':self.table.state.get('location'),'step':after.get('step',0),
                    'scope':'observed failure in this state, not universal impossibility'})
        if p.verb=='inspect' and self.pending and (current:=carried_counts(self.table)) is not None:
            sample=dict(self.pending,after_counts=current,
                consumed={x:n-current.get(x,0) for x,n in self.pending['before_counts'].items() if n>current.get(x,0)},
                scope='observed craft-to-inspection delta; environment effects not excluded; not a universal ratio')
            self.effects.append(sample);self.pending=None
        self.effects=self.effects[-16:];self.failures=self.failures[-12:]
        # Bound retained auxiliary evidence, including STM summary-only agent.
        for attr,limit in [('recipes',48),('places',16),('containers',12)]:
            data=getattr(self.table,attr)
            if len(data)>limit:
                keep=sorted(data,key=lambda k:(k==self.target,data[k].get('step',0)),reverse=True)[:limit]
                setattr(self.table,attr,{k:data[k] for k in keep})
        self.produced=dict(list(self.produced.items())[-32:])

    def records(self,obs):
        self.table.observe(obs);t=self.table;s=t.state;records=[]
        def add(kind,key,value,step,scope):
            records.append({'id':kind+':'+key,'kind':kind,'key':key,'value':value,'step':step,'scope':scope})
        now=s.get('step',0)
        add('goal',self.target,{'objective':self.goal,'observed_owned_lower_bound':t.count(self.target),
            'required':self.amount,'complete':(t.count(self.target) or 0)>=self.amount},now,'current public observation')
        relevant={self.target}
        for _ in range(8):
            expanded=relevant|{x for n in relevant for x in t.recipes.get(n,{}).get('ingredients',[])}
            if expanded==relevant:break
            relevant=expanded
        for name,r in sorted(t.recipes.items(),key=lambda x:(x[0]!=self.target,x[0] not in relevant,-x[1].get('step',0))):
            # Never portray sample average consumption as the true ingredient weight.
            add('recipe',name,{'ingredients':r.get('ingredients') or 'UNKNOWN',
                'stations':r.get('stations','UNKNOWN'),'quantities':'UNKNOWN unless an observed sample below'},r.get('step',0),'historically disclosed recipe names')
        for n,c in t.containers.items():
            add('container',n,{'last_observed_counts':c['counts'],'last_location':c['location'],
                'carried_now':t.carried(n),'transfer_access_now':t.access(n),'craft_access_now':t.access(n,True)},
                c.get('step',0),'last observed counts; UNKNOWN after observed mutation; exogenous changes not ruled out')
        for n,v in s.items():
            if n in {'hands','equipment','ground','location'}:add('current',n,v,now,'current public observation only')
        for e in reversed(self.effects[-8:]):
            add('effect',e['target']+':'+str(e['source_step']),{k:e[k] for k in ['requested','actual','consumed']},e['source_step'],e['scope'])
        for f in reversed(self.failures[-6:]):add('failure',f['target']+':'+str(f['step']),f['feedback'],f['step'],f['scope'])
        for name,n in self.produced.items():add('subgoal',name,{'observed_produced':n,'owned_now_lower_bound':t.count(name)},now,'production history is not current possession')
        for loc,data in sorted(t.places.items(),key=lambda x:-x[1]['step']):
            if loc!=s.get('location'):add('location',loc,data['objects'],data['step'],'historical last-seen objects, current presence UNKNOWN')
        add('uncertainty',self.target,{'missing_recipe_names':[x for x in sorted(relevant) if not t.recipes.get(x,{}).get('ingredients')],
            'unknown_quantity_rules':sorted(relevant),'unobserved_container_contents':[n for n,c in t.containers.items() if c['counts'] is None]},now,'explicit gaps, not negative facts')
        return records

    def render(self,obs):
        available=self.records(obs);chosen=[]
        prefix='Persistent public facts. UNKNOWN is not a negative fact. Historical locations and sample effects are not guaranteed current rules.\n'
        # Round-robin categories prevents a long recipe list from displacing all
        # observed effects, failures, subgoals or location uncertainty.
        kinds=['goal','uncertainty','recipe','effect','container','current','failure','subgoal','location']
        buckets={k:[r for r in available if r['kind']==k] for k in kinds}
        ordered=[]
        for i in range(max(map(len,buckets.values()),default=0)):
            ordered.extend(buckets[k][i] for k in kinds if i<len(buckets[k]))
        for record in ordered:
            candidate=prefix+'\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in chosen+[record])
            if len(chosen)>=self.MAX_RECORDS:break
            if len(candidate)<=self.MAX_CHARACTERS:chosen.append(record)
        text=prefix+'\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in chosen)
        return text,{'records':chosen,'available_record_ids':[r['id'] for r in available],
            'characters':len(text),'utf8_bytes':len(text.encode()),'token_proxy_char_div4':len(text)/4,
            'token_measurement':'character proxy only; billed full prompt tokens are in API usage',
            'extra_model_calls':0,'capacity_records':self.MAX_RECORDS,'capacity_characters':self.MAX_CHARACTERS}

    def to_dict(self):
        return {k:v.to_dict() if k=='table' else copy.deepcopy(v) for k,v in self.__dict__.items()}

    @classmethod
    def from_dict(cls,data):
        obj=cls();obj.__dict__.update(data);obj.table=ResourceTable(**data['table']);return obj
