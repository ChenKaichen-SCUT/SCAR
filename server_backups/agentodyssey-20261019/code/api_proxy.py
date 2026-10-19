"""Loopback-only DeepSeek transport and complete API usage accounting."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import pathlib,urllib.request,urllib.error,json,time,os,hashlib,threading,re,gzip
ROOT=pathlib.Path(__file__).resolve().parent
KEY=(ROOT/'.deepseek-key').read_text().strip()
MODEL='deepseek-flash'
LOCK=threading.Lock()
def log(run,event):
 folder=ROOT/'telemetry'/run;folder.mkdir(parents=True,exist_ok=True)
 with LOCK,(folder/'api_calls.jsonl').open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,status,obj):
  data=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status)
  self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  self.reply(200,{'object':'list','data':[{'id':MODEL,'object':'model','owned_by':'deepseek'}]})
 def do_POST(self):
  parts=self.path.strip('/').split('/');run=parts[0]
  if not re.fullmatch(r'[a-z0-9_-]{1,80}',run) or parts[1:]!=['v1','chat','completions']:return self.reply(404,{'error':'unsupported local route'})
  try:
   raw=self.rfile.read(int(self.headers.get('Content-Length','0')));payload=json.loads(raw)
   assert payload.get('model')==MODEL,'Unexpected model'
   assert 'tools' not in payload,'External tools are not part of this protocol'
   payload.pop('stream',None)
   requested=payload.pop('max_new_tokens',payload.get('max_tokens',4096))
   payload['max_tokens']=min(int(requested or 4096),4096)
   payload['thinking']={'type':'disabled'}
   # Flash ignores top_p in non-thinking mode; record effective configuration.
   payload.pop('top_p',None)
   body=json.dumps(payload,ensure_ascii=False).encode();started=time.time()
   call_id=str(time.time_ns())
   folder=ROOT/'telemetry'/run;folder.mkdir(parents=True,exist_ok=True)
   with gzip.open(folder/(call_id+'.request.json.gz'),'wb') as f:f.write(body)
   log(run,{'event':'started','call_id':call_id,'time':started,'request_bytes':len(body),'request_sha256':hashlib.sha256(body).hexdigest(),'max_tokens':payload['max_tokens'],'temperature':payload.get('temperature'),'thinking':'disabled','top_p_effective':1.0})
   req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=body,headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
   try:
    with urllib.request.urlopen(req,timeout=240) as response:result=json.load(response)
   except urllib.error.HTTPError as e:
    err=e.read().decode(errors='replace').replace(KEY,'[REDACTED]')
    log(run,{'event':'error','call_id':call_id,'time':time.time(),'latency_s':time.time()-started,'status':e.code,'error':err[:1000]})
    return self.reply(e.code,{'error':{'message':err[:1000],'type':'upstream_error'}})
   with gzip.open(folder/(call_id+'.response.json.gz'),'wt',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False)
   log(run,{'event':'completed','call_id':call_id,'time':time.time(),'latency_s':time.time()-started,'model':result.get('model'),'usage':result.get('usage'),'finish_reason':[c.get('finish_reason') for c in result.get('choices',[])],'system_fingerprint':result.get('system_fingerprint')})
   self.reply(200,result)
  except Exception as e:
   message=str(e).replace(KEY,'[REDACTED]')
   if 'call_id' in locals():log(run,{'event':'error','call_id':call_id,'time':time.time(),'latency_s':time.time()-started,'error':message})
   self.reply(502,{'error':{'message':message,'type':'proxy_error'}})
if __name__=='__main__':
 print('Serving loopback-only DeepSeek accounting proxy on 127.0.0.1:8088',flush=True)
 ThreadingHTTPServer(('127.0.0.1',8088),Handler).serve_forever()
