from scar_stage17.common import ROOT, ENGINE_COMMIT, load, write, sha, gzip_rows, read_gzip

RESULTS = ROOT / 'results/stage21'
REPORTS = ROOT / 'reports/stage21'
METHODS = ('SCAR21',)
NETWORK_ATTEMPTS = []


def deny_network():
    import os
    import socket
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    def blocked(*args, **kwargs):
        NETWORK_ATTEMPTS.append('blocked')
        raise RuntimeError('SCAR21 offline phase prohibits network/model/embedding calls')
    socket.create_connection = socket.socket.connect = socket.socket.connect_ex = socket.socket.sendto = blocked

