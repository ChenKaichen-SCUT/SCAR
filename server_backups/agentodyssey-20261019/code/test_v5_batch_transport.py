"""Loopback-only integration of routing and actual pre-request blocking."""
import json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from api_budget_guard import BudgetGuard
from api_proxy_v5_batch import make_handler
class TransportTests(unittest.TestCase):
    def test_routes_share_budget_and_do_not_retry_or_leak_quota(self):
        with tempfile.TemporaryDirectory() as tmp:
            limits=dict(calls=3,input_tokens=100000,uncached_input_tokens=100000,output_tokens=10000);per=dict(limits,calls=1)
            g=BudgetGuard(Path(tmp)/'b.sqlite',limits,per);calls=[];events=[]
            def fake(run,payload,rid):
                calls.append((run,payload));return {'usage':{'prompt_tokens':20,'completion_tokens':10,'prompt_cache_miss_tokens':5},'choices':[{'message':{'role':'assistant','content':'{}'}}]}
            server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(['a','b','c'],g,fake,lambda *x:events.append(x)));thread=threading.Thread(target=server.serve_forever);thread.start()
            try:
                def request(run):
                    data={'model':'deepseek-flash','messages':[{'role':'user','content':'test'}],'max_tokens':1000}
                    req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/{run}/v1/chat/completions',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
                    try:
                        with urllib.request.urlopen(req,timeout=3) as r:return r.status
                    except urllib.error.HTTPError as e:return e.code
                self.assertEqual(request('unregistered'),403);self.assertEqual(len(calls),0)
                self.assertEqual(request('a'),200);self.assertEqual(request('a'),429);self.assertEqual(len(calls),1)
                self.assertEqual(request('b'),200);self.assertEqual(request('c'),200);self.assertEqual(request('c'),429)
                self.assertEqual(g.usage()['calls'],3);self.assertEqual([x[0] for x in calls],['a','b','c'])
                self.assertTrue(all(x[1]['max_tokens']==768 and x[1]['thinking']=={'type':'disabled'} for x in calls))
            finally:server.shutdown();server.server_close();thread.join(timeout=3)
if __name__=='__main__':unittest.main(verbosity=2)
