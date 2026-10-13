"""Minimal synthetic reproduction of the official provider-injection loss."""
import socket
from pathlib import Path
from agents.rag.rag_agent_config import RAGAgentConfig
from agents.rag.voyager_agent import create_voyager_agent
from games.base.agent import Agent
from .analyze import write
from .config import RESULTS


class InjectedConfig(RAGAgentConfig):
    def get_llm(self, **kwargs): return 'injected provider sentinel'


def main():
    def deny(*a,**k):raise RuntimeError('No network in reproduction')
    socket.socket.connect=socket.create_connection=deny
    cfg=InjectedConfig(llm_provider='deepseek',llm_name='deepseek-flash')
    assert cfg.get_llm()=='injected provider sentinel'
    try:create_voyager_agent(Agent)('synthetic','synthetic',cfg)
    except ValueError as exc:
        assert str(exc)=='Unsupported LLM provider: deepseek'
        write(RESULTS/'voyager_config_reproduction.json',dict(passed=True,original_exception=str(exc),
              api_calls=0,game_content=False,cause='Voyager reconstructs the subclass config as a plain VoyagerAgentConfig and loses get_llm injection',
              fixed_regression='preflight.json: all five interfaces preserve provider identity'))
    else:raise AssertionError('Original compatibility error was not reproduced')


if __name__=='__main__':main()
