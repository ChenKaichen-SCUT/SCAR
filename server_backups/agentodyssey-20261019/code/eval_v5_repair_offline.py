"""Check exact prefix reconstruction with saved outputs; external network forbidden."""
import gzip,json,os,runpy,socket
from pathlib import Path
from unittest.mock import patch
from agents.feedback_v5_agent import GuardedModel
records=[]
for source_id in json.loads(os.environ['AO_PREFIX_SOURCES']):
    source=Path(__file__).resolve().parent/'telemetry'/source_id
    for line in (source/'api_calls.jsonl').read_text().splitlines():
        e=json.loads(line)
        if e['event']!='completed':continue
        with gzip.open(source/(e['call_id']+'.request.json.gz'),'rt') as f:req=json.load(f)
        with gzip.open(source/(e['call_id']+'.response.json.gz'),'rt') as f:res=json.load(f)
        records.append((req,res))
index=0
def replay(self,user_prompt,system_prompt):
    global index
    assert index<len(records),'Offline reconstruction requested an extra completion'
    req,res=records[index];index+=1
    assert req['messages']==[{'role':'system','content':system_prompt},{'role':'user','content':user_prompt}],('Offline prompt mismatch',index)
    return {'response':res['choices'][0]['message']['content'],'num_input_tokens':res['usage']['prompt_tokens'],'num_output_tokens':res['usage']['completion_tokens']}
with patch.object(GuardedModel,'generate',replay),patch.object(socket.socket,'connect',side_effect=AssertionError('Offline replay attempted network')):
    runpy.run_path(__file__.replace('eval_v5_repair_offline.py','eval_v5_repair_continue.py'),run_name='__main__')
assert index==len(records),(index,len(records))
