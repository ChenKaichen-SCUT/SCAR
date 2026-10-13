"""No copied decision rules; execute the original Stage18 code objects.

Only global class references are rebound to preserve the configured horizon on
detached trial controllers, syntax rollback, and memory restore. The public-goal
channel is the pre-existing Controller.follow_public interface; no quest parser,
subgoal selection, or knowledge from a game file is added here.
"""
import types
from functools import lru_cache
from scar_stage18.agent import Agent18
from scar_stage18.controller import Controller18
from scar_stage16.controller import BaselineController
from scar_stage17.budget_adapter import horizon_function


def rebind(fn, **bindings):
    namespace = dict(fn.__globals__)
    namespace.update(bindings)
    return types.FunctionType(fn.__code__, namespace, fn.__name__, fn.__defaults__, fn.__closure__)


class Budget300Controller(BaselineController):
    finish = horizon_function(BaselineController.finish, 300)
    choose = horizon_function(BaselineController.choose, 300)


class Controller18Fixed(Controller18):
    finish = Budget300Controller.finish
    choose = rebind(Controller18.choose, Budget100Controller=Budget300Controller)
    legacy_copy = rebind(Controller18.legacy_copy, Budget100Controller=Budget300Controller)


class Stage18Fixed(Agent18):
    __init__ = rebind(Agent18.__init__, Controller18=Controller18Fixed)
    _act = rebind(Agent18._act, Controller18=Controller18Fixed)
    load_memory = rebind(Agent18.load_memory, Controller18=Controller18Fixed)

    def initialize_official(self, observation):
        """Wire the original public-goal input, without a custom crafting target."""
        if self.controller.in_episode or self.short_term_memory:
            raise ValueError('A game requires empty memory and a fresh controller')
        self.controller.table.observe(observation)
        action = self.controller.table.state.get('public_goal') or ''
        objective = 'Follow the current publicly announced task.'
        self.controller.set_goal(action, objective, follow_public=True)
        self.facts.set_goal(action, objective)

    def observe_transition(self, before, action, after):
        super().observe_transition(before, action, after)
        # Keep the existing model fact view synchronized with the existing
        # controller goal channel. No new goal is inferred or selected.
        self.facts.set_goal(self.controller.target, self.controller.objective)


@lru_cache(None)
def create_stage18_fixed(base):
    return type('Stage18Fixed__' + base.__module__ + '.' + base.__name__,
                (Stage18Fixed, base), {'__module__': base.__module__, '__agent__': base})
