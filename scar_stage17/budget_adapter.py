"""User-authorized P3 horizon adaptation; Stage16 source is immutable.

The function clone replaces only the referenced EPISODE_ACTIONS global in an
isolated globals dictionary. Code objects, FINISH_WINDOW, dispatch and thresholds
are exactly Stage16. This avoids both policy transcription and global mutation.
"""
import types
from scar_stage16.controller import BaselineController


def horizon_function(fn, horizon=100):
    namespace = dict(fn.__globals__)
    namespace['EPISODE_ACTIONS'] = horizon
    return types.FunctionType(fn.__code__, namespace, fn.__name__, fn.__defaults__, fn.__closure__)


class Budget100Controller(BaselineController):
    finish = horizon_function(BaselineController.finish)
    choose = horizon_function(BaselineController.choose)


def adapt(agent):
    assert type(agent.controller) in (BaselineController, Budget100Controller)
    agent.controller.__class__ = Budget100Controller
    return agent
