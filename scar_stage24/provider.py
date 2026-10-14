"""Unchanged Stage22 transport; isolate its process-global RNG side effects."""
import random
import numpy as np
from scar_stage22.provider import Provider

class SharedProvider(Provider):
    def generate(self,*a,**kw):
        py,ns=random.getstate(),np.random.get_state()
        try:return super().generate(*a,**kw)
        finally:random.setstate(py);np.random.set_state(ns)
