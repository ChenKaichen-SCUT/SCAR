"""Opt-in loopback transport. Reserve shared budget before contacting the provider."""
import argparse,gzip,json,threading,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from api_budget_guard import BudgetGuard,BudgetStopped,guarded_generate
R=Path(__file__).resolve().parent

def serve(protocol):
    cfg=json.loads(Path(protocol).read_text());assert cfg['paid_execution_explicitly_enabled'] is True
    guard=BudgetGuard(R/cfg['budget_db'],cfg['limits'],cfg['per_run_limits']);run=cfg['run_id'];lock=threading.Lock()
    key=(R/'.deepseek-key').read_text().strip();folder=R/'telemetry'/run;folder.mkdir(parents=True,exist_ok=False)
    def log(event):
        with lock,(folder/'api_calls.jsonl').open('a') as f:f.write(json.dumps(event)+'\n')
    def upstream(payload,rid):
        with gzip.open(folder/(rid+'.request.json.gz'),'wt',encoding='utf-8') as f:json.dump(payload,f)
        log({'event':'started','call_id':rid})
        req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=120) as response:result=json.load(response)
        except Exception as e:log({'event':'error','call_id':rid,'type':type(e).__name__});raise
        with gzip.open(folder/(rid+'.response.json.gz'),'wt',encoding='utf-8') as f:json.dump(result,f)
        log({'event':'completed','call_id':rid,'usage':result.get('usage'),'model':result.get('model')});return result
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,body):
            data=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_POST(self):
            if self.path!='/'+run+'/v1/chat/completions':return self.reply(403,{'error':{'message':'unregistered run'}})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n>1_000_000:raise BudgetStopped('request_byte_limit')
                p=json.loads(self.rfile.read(n));assert p.get('model')=='deepseek-flash' and not p.get('tools') and not p.get('stream')
                p['max_tokens']=min(int(p.get('max_tokens',768)),768);p['thinking']={'type':'disabled'};p.pop('top_p',None)
                result=guarded_generate(guard,run,p,upstream);self.reply(200,result)
            except BudgetStopped as e:log({'event':'budget_or_safety_stop','reason':str(e)});self.reply(429,{'error':{'message':str(e),'type':'budget_stop'}})
            except Exception as e:self.reply(400,{'error':{'message':type(e).__name__}})
    ThreadingHTTPServer(('127.0.0.1',8094),Handler).serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);a=p.parse_args();serve(a.protocol)
