"""Zero-API native checks can overlap remaining first-run model experiments."""
import argparse
import concurrent.futures
import json
import socket
from .config import RESULTS,GAMES,METHODS
from .verify import cached_replay


def job(entry):
    def deny(*a,**k):raise RuntimeError('Offline native replay: network forbidden')
    socket.create_connection=socket.socket.connect=socket.socket.connect_ex=deny
    result,_=cached_replay(entry)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--exclude-metropolis-scar',action='store_true');args=parser.parse_args()
    entries=[(g,m) for g in GAMES for m in METHODS if (RESULTS/'runs'/f'{g}__{m}'/'summary.json').exists()
             and not (args.exclude_metropolis_scar and (g,m)==('metropolis','Stage18-Fixed'))]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(job,entries):print(json.dumps(row),flush=True)


if __name__=='__main__':main()
