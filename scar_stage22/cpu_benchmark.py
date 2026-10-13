"""Reproduce the game-independent CPU-only embedding throughput measurement."""
import time
import torch
from providers.huggingface import hfEmbeddingModel
from scar.io import atomic_json
from .config import EMBEDDING_PATH,RESULTS


def main():
    model=hfEmbeddingModel(EMBEDDING_PATH,'cpu')
    text=['Generic observation with an object, a location and a possible action. '*90]
    vectors=[];records=[]
    for threads in (1,4):
        torch.set_num_threads(threads)
        start=time.perf_counter();vectors.append(model.encode(text))
        records.append(dict(cpu_threads=threads,seconds=time.perf_counter()-start))
    destination=RESULTS/'cpu_embedding_benchmark.json'
    assert not destination.exists(),'Preserve the original resource benchmark receipt'
    atomic_json(destination,dict(records=records,max_abs_difference=float((vectors[0]-vectors[1]).abs().max()),
                cosine_similarity=float((vectors[0]*vectors[1]).sum()),api_calls=0,game_content=False,
                purpose='resource-only benchmark; no policy changes'))


if __name__=='__main__':main()
