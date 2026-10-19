"""Same transport and accounting, explicitly allowing up to 128 API calls."""
import threading
from http.server import ThreadingHTTPServer
from api_proxy import Handler
LIMIT=threading.BoundedSemaphore(128)
class LimitedHandler(Handler):
 def do_POST(self):
  with LIMIT:super().do_POST()
class Server(ThreadingHTTPServer):
 request_queue_size=128
 daemon_threads=True
if __name__=='__main__':
 print('DeepSeek accounting proxy: 128-call ceiling; six sequential trajectories.',flush=True)
 Server(('127.0.0.1',8088),LimitedHandler).serve_forever()
