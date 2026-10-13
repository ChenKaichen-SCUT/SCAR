from scar_stage17.common import ROOT, ENGINE_COMMIT, load, write, sha, gzip_rows, read_gzip

RESULTS = ROOT/'results/stage18'
REPORTS = ROOT/'reports/stage18'
METHODS = ('SCAR18',)


def deny_network():
    """Zero-API checks are enforced, not merely promised."""
    import socket
    def blocked(*args, **kwargs):
        raise RuntimeError('Network disabled for Stage18 offline verification')
    socket.create_connection = blocked
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
