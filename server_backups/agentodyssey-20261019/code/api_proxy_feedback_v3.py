"""Isolated telemetry for the three improved trajectories; 128-call ceiling."""
import threading
from http.server import ThreadingHTTPServer
from api_proxy import Handler
LIMIT=threading.BoundedSemaphore(128)
ALLOWED={g+'__feedback_v3'+suffix for g in ['remnant','mark','metropolis'] for suffix in ['', '__controller']}
class LimitedHandler(Handler):
    def do_POST(self):
        if self.path.strip('/').split('/')[0] not in ALLOWED:
            return self.reply(403,{'error':'Only new improved-algorithm runs are allowed.'})
        with LIMIT:super().do_POST()
class Server(ThreadingHTTPServer):
    request_queue_size=128
    daemon_threads=True
if __name__=='__main__':
    Server(('127.0.0.1',8092),LimitedHandler).serve_forever()
