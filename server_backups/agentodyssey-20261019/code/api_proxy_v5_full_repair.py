"""Replay already-paid prefix exactly, then continue against amended persistent budget."""
import argparse,gzip,json,threading,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from budget_guard_v5_full import BudgetGuard,BudgetStopped,guarded_generate
R=Path(__file__).resolve().parent
def read_rows(path):return [json.loads(x) for x in path.read_text().splitlines() if x]
def serve(protocol):
    cfg=json.loads(Path(protocol).read_text());assert cfg['paid_execution_explicitly_enabled']
    guard=BudgetGuard(R/cfg['budget_db'],cfg['limits'],cfg['per_run_limits']);specs={s['id']:s for s in cfg['runs']};lock=threading.Lock();cache={};folders={}
    for rid,s in specs.items():
        folder=R/'telemetry'/rid;folder.mkdir(parents=True,exist_ok=False);folders[rid]=folder
        cache[rid]=[]
        for source_id in s['cache_sources']:
            source=R/'telemetry'/source_id
            done=[x for x in read_rows(source/'api_calls.jsonl') if x['event']=='completed']
            for e in done:
                cid=e['call_id']
                with gzip.open(source/(cid+'.request.json.gz'),'rt') as f:req=json.load(f)
                with gzip.open(source/(cid+'.response.json.gz'),'rt') as f:res=json.load(f)
                cache[rid].append((cid,req,res))
        assert len(cache[rid])==s['cached_calls']
    key=(R/'.deepseek-key').read_text().strip()
    def log(run,event):
        with lock,(folders[run]/'api_calls.jsonl').open('a') as f:f.write(json.dumps(event)+'\n')
    def upstream(run,payload,cid):
        with gzip.open(folders[run]/(cid+'.request.json.gz'),'wt',encoding='utf-8') as f:json.dump(payload,f)
        log(run,{'event':'started','call_id':cid})
        req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=120) as resp:result=json.load(resp)
        except Exception as e:log(run,{'event':'error','call_id':cid,'type':type(e).__name__});raise
        with gzip.open(folders[run]/(cid+'.response.json.gz'),'wt',encoding='utf-8') as f:json.dump(result,f)
        log(run,{'event':'completed','call_id':cid,'usage':result.get('usage'),'model':result.get('model'),'finish_reason':result.get('choices',[{}])[0].get('finish_reason')});return result
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def reply(self,code,result):
            data=json.dumps(result).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_POST(self):
            rid=next((r for r in specs if self.path=='/'+r+'/v1/chat/completions'),None)
            if rid is None:return self.reply(403,{'error':{'message':'unregistered run'}})
            try:
                n=int(self.headers.get('Content-Length','0'));assert 0<n<=1_000_000
                p=json.loads(self.rfile.read(n));assert p.get('model')=='deepseek-flash' and not p.get('stream') and not p.get('tools')
                p['max_tokens']=min(int(p.get('max_tokens',768)),768);p['thinking']={'type':'disabled'};p.pop('top_p',None)
                if cache[rid]:
                    cid,old,result=cache[rid][0]
                    if p!=old:raise BudgetStopped('prefix_reconstruction_mismatch_no_new_call')
                    cache[rid].pop(0);log(rid,{'event':'cached_prefix_replay','source_call_id':cid,'remaining':len(cache[rid]),'new_provider_calls':0})
                else:result=guarded_generate(guard,specs[rid]['budget_scope'],p,lambda payload,cid:upstream(rid,payload,cid))
                self.reply(200,result)
            except BudgetStopped as e:log(rid,{'event':'budget_or_safety_stop','reason':str(e)});self.reply(429,{'error':{'message':str(e),'type':'budget_stop'}})
            except Exception as e:log(rid,{'event':'request_error','type':type(e).__name__});self.reply(400,{'error':{'message':type(e).__name__}})
    ThreadingHTTPServer(('127.0.0.1',8094),Handler).serve_forever()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);a=p.parse_args();serve(a.protocol)
