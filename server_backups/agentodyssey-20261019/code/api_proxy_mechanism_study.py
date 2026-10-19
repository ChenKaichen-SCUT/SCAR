"""Isolated study routes and 128-request ceiling. One paid trajectory per condition."""
import threading
from http.server import ThreadingHTTPServer
from api_proxy import Handler
LIMIT=threading.BoundedSemaphore(128)
IDS=[g+'__ab_'+v for v in ['no_checks','no_execution','no_repeat','no_hypothesis'] for g in ['remnant','metropolis']]+[g+'__study_v4' for g in ['remnant','mark','metropolis']]
ALLOWED={rid+suffix for rid in IDS for suffix in ['', '__controller']}
class LimitedHandler(Handler):
    def do_POST(self):
        if self.path.strip('/').split('/')[0] not in ALLOWED:return self.reply(403,{'error':'Only registered mechanism study conditions are allowed.'})
        with LIMIT:super().do_POST()
class Server(ThreadingHTTPServer):
    request_queue_size=128
    daemon_threads=True
if __name__=='__main__':Server(('127.0.0.1',8093),LimitedHandler).serve_forever()
