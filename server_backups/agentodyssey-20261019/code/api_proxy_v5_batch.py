"""Multi-game routing only; frozen v5 BudgetGuard still reserves every call."""
import argparse,gzip,json,threading,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from api_budget_guard import BudgetGuard,BudgetStopped,guarded_generate
R=Path(__file__).resolve().parent

def make_handler(runs,guard,upstream,log,replay=None):
    routes={'/'+run+'/v1/chat/completions':run for run in runs}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,body):
            data=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_POST(self):
            run=routes.get(self.path)
            if run is None:return self.reply(403,{'error':{'message':'unregistered run'}})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=1_000_000:raise BudgetStopped('request_byte_limit')
                payload=json.loads(self.rfile.read(n));assert payload.get('model')=='deepseek-flash' and not payload.get('tools') and not payload.get('stream')
                payload['max_tokens']=min(int(payload.get('max_tokens',768)),768);payload['thinking']={'type':'disabled'};payload.pop('top_p',None)
                result=replay(run,payload) if replay else None
                if result is None:result=guarded_generate(guard,run,payload,lambda p,rid:upstream(run,p,rid))
                self.reply(200,result)
            except BudgetStopped as e:log(run,{'event':'budget_or_safety_stop','reason':str(e)});self.reply(429,{'error':{'message':str(e),'type':'budget_stop'}})
            except Exception as e:log(run,{'event':'request_error','type':type(e).__name__});self.reply(400,{'error':{'message':type(e).__name__}})
    return Handler

def serve(path):
    cfg=json.loads(Path(path).read_text());assert cfg['paid_execution_explicitly_enabled'] is True
    runs=[x['id'] for x in cfg['runs']];guard=BudgetGuard(R/cfg['budget_db'],cfg['limits'],cfg['per_run_limits']);lock=threading.Lock()
    folders={r:R/'telemetry'/r for r in runs}
    recovery=cfg.get('startup_recovery',{});cached={}
    for run,f in folders.items():
        f.mkdir(parents=True,exist_ok=bool(recovery))
        if recovery:
            original=recovery['reuse_completed_call'][run]
            with gzip.open(f/(original+'.request.json.gz'),'rt') as q:request=json.load(q)
            with gzip.open(f/(original+'.response.json.gz'),'rt') as q:response=json.load(q)
            cached[run]=(original,request,response)
    key=(R/'.deepseek-key').read_text().strip()
    def log(run,event):
        with lock,(folders[run]/'api_calls.jsonl').open('a') as f:f.write(json.dumps(event)+'\n')
    def replay(run,payload):
        with lock:
            item=cached.get(run)
            if item is None:return None
            original,request,response=item
            if request!=payload:raise BudgetStopped('cached_startup_request_mismatch_no_provider_call')
            cached.pop(run)
        log(run,{'event':'replayed_paid_response','original_call_id':original,'new_provider_calls':0});return response
    def upstream(run,payload,rid):
        folder=folders[run]
        with gzip.open(folder/(rid+'.request.json.gz'),'wt',encoding='utf-8') as f:json.dump(payload,f)
        log(run,{'event':'started','call_id':rid})
        req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=120) as response:result=json.load(response)
        except Exception as e:log(run,{'event':'error','call_id':rid,'type':type(e).__name__});raise
        with gzip.open(folder/(rid+'.response.json.gz'),'wt',encoding='utf-8') as f:json.dump(result,f)
        log(run,{'event':'completed','call_id':rid,'usage':result.get('usage'),'model':result.get('model'),'finish_reason':result.get('choices',[{}])[0].get('finish_reason')});return result
    ThreadingHTTPServer(('127.0.0.1',8094),make_handler(runs,guard,upstream,log,replay)).serve_forever()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);args=p.parse_args();serve(args.protocol)
