from scar_stage17.common import ROOT, ENGINE_COMMIT, load, write, sha, gzip_rows, read_gzip

RESULTS = ROOT / 'results/stage20'
REPORTS = ROOT / 'reports/stage20'
METHODS = ('SCAR20',)


def deny_network():
    import socket
    def blocked(*args, **kwargs):
        raise RuntimeError('Network disabled for SCAR20 offline verification')
    socket.create_connection = socket.socket.connect = socket.socket.connect_ex = blocked
