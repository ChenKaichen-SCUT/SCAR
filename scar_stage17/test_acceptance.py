import copy
import json
from pathlib import Path
import pytest
from scar_stage16.controller import BaselineController
from scar_stage17.budget_adapter import Budget100Controller
from scar_stage17.preflight import MockProvider
from scar_stage17.methods import make_method
from third_party_adapters.adaplanner_agentodyssey import check_condition,validate_plan


def test_horizon_changes_only_authorized_late_finish():
    def prepare(cls):
        c=cls();c.target='craft 1 widget';c.amount=1;c.step16=50
        c.table.state={'hands':{},'ground':{}};c.table.recipes={'widget':{'quantities':{'part':1}}}
        c.table.count=lambda item:0;c.ready=lambda item:True;c._batch_action=lambda a:a
        return c
    old=prepare(BaselineController);new=prepare(Budget100Controller)
    assert old.finish('wait')[0] is None
    assert new.finish('wait')[0]=='craft 1 widget'
    assert new.finish.__globals__['FINISH_WINDOW']==old.finish.__globals__['FINISH_WINDOW']==6
    for step in range(36):
        old.step16=new.step16=step
        assert old.finish('wait')==new.finish('wait')


def test_adaplanner_real_assertion_revision_and_resume(tmp_path):
    provider=MockProvider();agent=make_method('A3','robot_kingdom',provider,'Obtain old dev goal','bandage_roll',[],tmp_path)
    obs={'step':0,'text':'Current Location: World, courtyard\n\nI waited.\n\nI am holding no objects.\nI have equipped no objects.\nI see no objects near me.\nI see no one nearby.\nNeighboring areas: no neighboring areas.\n'}
    action=agent.act(obs)[0];assert action=='wait'
    failed=dict(obs,step=1,text=obs['text'].replace('I waited.','Cannot perform wait.'))
    agent.observe_transition(obs,action,failed);assert agent.deviation
    agent.act(failed)
    phases=[r['phase'] for r in provider.calls]
    assert phases==['plan','plan_check','ask_LLM','revision','plan_check','resume','ask_LLM']
    assert agent.variables=={'neutral':'wait'} and len(agent.versions)==2
    agent.save_memory(str(tmp_path))
    resumed=make_method('A3','robot_kingdom',MockProvider(),'Obtain old dev goal','bandage_roll',[],tmp_path)
    resumed.load_memory(str(tmp_path));assert resumed.export()==agent.export()


def test_dag_public_material_acquisition_and_recipe(tmp_path):
    agent=make_method('A4','robot_kingdom',None,'Obtain widget','widget',[],tmp_path)
    t=agent.table;t.state={'location':'room','ground':{'part':2,'station':1},'hands':{},'equipment':{},'neighbors':[]}
    t.recipes={'widget':{'ingredients':['part'],'quantities':{'part':2},'stations':['station']}}
    agent.decision={};assert agent.need('widget',1)=='pick up part'
    t.state['hands']={'part':2};agent.decision={};assert agent.need('widget',1)=='craft 1 widget'
    t.state['hands']={};t.recipes['partial']={'ingredients':['part'],'quantities':None}
    agent.decision={};assert agent.need('partial',1)=='pick up part'
    # UNKNOWN relationship triggers bounded real trials, never hidden graph access.
    agent.decision={};assert agent.need('unknown',1)=='craft 1 unknown'
    source=Path(__file__).with_name('dag.py').read_text()
    assert 'from scar_stage16.controller' not in source and 'from .oracle' not in source and 'env.world' not in source


def test_long_context_and_stm_retention(tmp_path):
    for method in ('A1','A2'):
        a=make_method(method,'robot_kingdom',MockProvider(),'Goal','bandage_roll',[],tmp_path)
        for i in range(150):a.memorize('unique history marker '+str(i))
        a.save_memory(str(tmp_path))
        b=make_method(method,'robot_kingdom',MockProvider(),'Goal','bandage_roll',[],tmp_path);b.load_memory(str(tmp_path))
        if method=='A1':assert b.short_term_memory==a.short_term_memory and len(b.short_term_memory)==5
        else:assert 'unique history marker 0\n' in b.memory.context and 'unique history marker 149\n' in b.memory.context


def test_paid_parse_retry_and_crash_resume_cache(tmp_path,monkeypatch):
    import scar_stage17.provider as module
    calls=[]
    class Response:
        def __init__(self,valid):self.valid=valid
        def model_dump(self):
            return dict(choices=[{'message':{'content':json.dumps({'action':'wait','reasoning':'ok'} if self.valid else {'bad':'format'})}}],usage=dict(prompt_tokens=100,completion_tokens=20,prompt_cache_hit_tokens=0))
    class Client:
        def __init__(self):self.chat=self;self.completions=self
        def create(self,**kwargs):calls.append(kwargs);return Response(len(calls)>1)
    monkeypatch.setattr('openai.OpenAI',lambda **kwargs:Client())
    monkeypatch.setattr(module,'read_key',lambda path:'nonsecret-test-fixture')
    monkeypatch.setattr(module.time,'sleep',lambda n:None)
    p=module.SharedDeepSeekProvider(tmp_path/'run',tmp_path/'ledger.sqlite',None);p.begin_step(1)
    out=p.generate('public observation','public system')
    assert out['parsed']['action']=='wait' and len(calls)==2
    rows=[json.loads(line) for line in p.audit.read_text().splitlines()]
    assert [r['status'] for r in rows]==['invalid_response','ok']
    assert all(r['charged_or_reserved_usd']>0 for r in rows)
    resumed=module.SharedDeepSeekProvider(tmp_path/'run',tmp_path/'ledger.sqlite',None);resumed.begin_step(1)
    assert resumed.generate('public observation','public system')==out and len(calls)==2
    resumed.begin_step(1)
    with pytest.raises(RuntimeError,match='changed'):resumed.generate('changed observation','public system')
    assert all(c['temperature']==0.7 and c['max_tokens']==768 and c['extra_body']=={'thinking':{'type':'disabled'}} for c in calls)
