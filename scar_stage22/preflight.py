"""Synthetic interface acceptance. Never opens a ranking game or trajectory."""
import copy
import json
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import torch
from scar.io import atomic_json
from scar_stage18.controller import Controller18
from scar_stage18.agent import Agent18
from scar_stage18.tests.test_execution import ExecutionTests, controller
from scar_stage18_fixed.agent import Controller18Fixed, Stage18Fixed, Budget300Controller
from agents.fixed_size.fixed_size_memory_agent_config import FixedSizeMemoryAgentConfig
from agents.fixed_size.short_term_memory_agent import ShortTermMemoryAgent
from games.base.agent import Agent
from .config import RESULTS, METHODS
from .integration import make_agent, MemoryConfig, VoyagerConfig


OBS = dict(step=0, text='Current Location: test_site, workshop\n'
           'Required action: `inspect pebble`\n'
           'I am holding nothing.\nI have equipped nothing.\n'
           'I see 2 pebble near me.\nI see no one nearby.\n'
           'Neighboring areas: yard\nMy health is at 100.')


class Mock:
    def __init__(self): self.calls = []
    def generate(self, user_prompt, system_prompt=None, **kwargs):
        self.calls.append(dict(user=user_prompt, system=system_prompt))
        if 'automatic curriculum' in system_prompt: value = dict(task='inspect pebble', context='public task')
        elif 'judge whether' in system_prompt: value = dict(success=False, critique='continue')
        elif 'skill distillation' in system_prompt: value = dict(skill_name='inspection', skill_desc='inspect an object', skill_body='inspect pebble')
        else: value = dict(action='inspect pebble', reasoning='Synthetic interface action.')
        return dict(response=json.dumps(value), num_input_tokens=1, num_output_tokens=1)


class MockEmbedding:
    def encode(self, texts): return torch.ones(len(texts), 4) / 2


class InterfaceTests(unittest.TestCase):
    def test_original_stm_missing_method_reproduced(self):
        original = FixedSizeMemoryAgentConfig()
        with self.assertRaises(AttributeError): original.construct_user_prompt_long_context('', 'synthetic')
        fixed = MemoryConfig()
        self.assertEqual(fixed.construct_user_prompt_long_context('past', 'present'),
                         'My Memories: pastMy Current Observation: present\n' + fixed.action_prompt)

    def test_original_code_objects_preserved(self):
        self.assertIs(Controller18Fixed.choose.__code__, Controller18.choose.__code__)
        self.assertIs(Controller18Fixed.legacy_copy.__code__, Controller18.legacy_copy.__code__)
        self.assertIs(Stage18Fixed._act.__code__, Agent18._act.__code__)
        self.assertIs(Stage18Fixed.__init__.__code__, Agent18.__init__.__code__)
        self.assertIs(Stage18Fixed.load_memory.__code__, Agent18.load_memory.__code__)
        self.assertEqual(Controller18Fixed.finish.__globals__['EPISODE_ACTIONS'], 300)
        self.assertEqual(Budget300Controller.choose.__globals__['EPISODE_ACTIONS'], 300)
        self.assertEqual(Controller18Fixed.choose.__globals__['Budget100Controller'], Budget300Controller)
        self.assertEqual(Controller18Fixed().legacy_copy().finish.__globals__['EPISODE_ACTIONS'], 300)
        self.assertEqual(Controller18().finish.__globals__['EPISODE_ACTIONS'], 100)

    def test_late_horizon_minimal_reproduction(self):
        old = controller(owned=2)
        old.step16 = 99
        fixed = Controller18Fixed.from_dict(old.to_dict())
        self.assertIsNone(old.finish('inspect ore')[0])
        self.assertEqual(fixed.finish('inspect ore')[0], 'craft 1 widget')
        restored = Controller18Fixed.from_dict(fixed.to_dict())
        self.assertEqual(restored.finish('inspect ore'), fixed.finish('inspect ore'))

    def test_synthetic_decision_equivalence(self):
        checked = 0
        for owned in range(4):
            for held in range(2):
                for action in ('inspect ore', 'store 17 ore inventory', 'craft 1 widget', 'pick up ore', 'wait'):
                    old = controller(owned=owned, held=held)
                    fixed = Controller18Fixed.from_dict(old.to_dict())
                    obs = dict(step=8, text='Current Location: test_site, workshop\n'
                               'I am holding ' + (str(held)+' ore' if held else 'nothing') + '.\n'
                               'I have equipped 1 bag.\nI see 17 ore, 1 bench near me.\n'
                               'Neighboring areas: yard\nI see no one nearby.\nMy health is at 100.')
                    self.assertEqual(old.choose(obs, action), fixed.choose(obs, action))
                    # The only bookkeeping difference is remaining_actions.
                    def strip(x):
                        if isinstance(x, dict): return {k:strip(v) for k,v in x.items() if k!='remaining_actions'}
                        if isinstance(x, list): return [strip(v) for v in x]
                        return x
                    self.assertEqual(strip(old.to_dict()), strip(fixed.to_dict()))
                    checked += 1
        self.assertEqual(checked, 40)

    def test_all_five_interfaces_and_memory_reset(self):
        original_embed = VoyagerConfig.get_embedder
        VoyagerConfig.get_embedder = lambda self: MockEmbedding()
        try:
            for method in METHODS:
                with self.subTest(method=method), tempfile.TemporaryDirectory() as directory:
                    folder = Path(directory); memory = folder/'memory'; memory.mkdir()
                    provider = Mock()
                    agent = make_agent(method, None, provider, memory, base=Agent)
                    self.assertIs(agent.llm, provider)
                    if method == 'Stage18-Fixed': agent.initialize_official(OBS)
                    action, *_ = agent.act(copy.deepcopy(OBS))
                    self.assertIsInstance(action, str)
                    if hasattr(agent, 'observe_transition'):
                        after = dict(OBS, step=1, text=OBS['text'].replace('inspect pebble', 'pick up pebble'))
                        agent.observe_transition(OBS, action, after)
                        self.assertEqual(agent.controller.target, 'pick up pebble')
                        self.assertEqual(agent.facts.target, 'pebble')
                    if method == 'VoyagerAgent':
                        self.assertEqual(len(provider.calls), 2)
                        agent.act(copy.deepcopy(OBS))
                        self.assertEqual(len(provider.calls), 4)
                        self.assertEqual(len(agent.trace), 2)
                    if hasattr(agent, 'save_memory'):
                        agent.save_memory(str(memory))
                        other = make_agent(method, None, Mock(), folder/'fresh', base=Agent)
                        other.load_memory(str(memory))
                        if method == 'Stage18-Fixed':
                            self.assertEqual(agent.controller.to_dict(), other.controller.to_dict())
                            self.assertIsInstance(other.controller, Controller18Fixed)
                        if method == 'VoyagerAgent':
                            self.assertEqual(agent.trace, other.trace)
                            self.assertEqual(agent.current_task, other.current_task)
                    new = make_agent(method, None, Mock(), folder/'independent', base=Agent)
                    if hasattr(new, 'short_term_memory'): self.assertEqual(new.short_term_memory, [])
                    if method == 'VoyagerAgent':
                        self.assertEqual(new.trace, []); self.assertEqual(len(new.skill_lib), 0)
                    if method == 'LongContextAgent': self.assertEqual(new.memory.context, '')
        finally: VoyagerConfig.get_embedder = original_embed

    def test_official_parser_fallback_is_shared(self):
        for cls in (MemoryConfig, VoyagerConfig):
            self.assertEqual(cls().response_parser('broken')['action'], 'wait')
            self.assertEqual(cls().response_parser('{"reasoning":"test","action":"inspect pebble"}')['action'], 'inspect pebble')


def main():
    def deny(*args, **kwargs): raise RuntimeError('No network in synthetic preflight')
    socket.create_connection = socket.socket.connect = socket.socket.connect_ex = deny
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(ExecutionTests),
                               unittest.defaultTestLoader.loadTestsFromTestCase(InterfaceTests)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    import sys
    forbidden = [n for n in sys.modules if n.startswith(('scar_stage19', 'scar_stage20', 'scar_stage21'))]
    receipt = dict(passed=result.wasSuccessful() and not forbidden, tests=result.testsRun,
                   failures=len(result.failures), errors=len(result.errors), api_calls=0,
                   synthetic_decision_pairs=40, ranking_games_loaded=[], network_denied=True,
                   later_stage_modules_imported=forbidden)
    atomic_json(RESULTS/'preflight.json', receipt)
    assert receipt['passed'], receipt


if __name__ == '__main__': main()
