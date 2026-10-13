import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT/'results/stage17'
METHODS = ('A0', 'A1', 'A2', 'A3', 'A4')
BASE_COMMIT = '1b650b41dea958d22e8415d8b23770f2454a8028'
ENGINE_COMMIT = '248430692a9d4a61d38c6c03ab2126287faaf450'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    from scar.io import atomic_json
    atomic_json(Path(path), data)


def gzip_rows(path, rows):
    with Path(path).open('wb') as stream:
        with gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0) as out:
            for row in rows:
                out.write((json.dumps(row, ensure_ascii=False, separators=(',', ':'))+'\n').encode())


def read_gzip(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]
