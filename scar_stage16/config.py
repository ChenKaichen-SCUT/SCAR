"""Frozen policy choices; no experimental multi-module dispatch."""
from dataclasses import dataclass

VARIANTS = ('S1', 'S1_P1', 'S1_P1_P3')
BASE_COMMIT = 'd747793d1a76a14004e43c8ad698b768afcf1f24'
SCHEMA_VERSION = 1
MODEL = 'deepseek-flash'
TEMPERATURE = 0.7
MAX_TOKENS = 768
STM_SIZE = 5
EMBEDDING_MODEL = 'Qwen/Qwen3-Embedding-0.6B'
EMBEDDING_REVISION = '97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'
EPISODE_ACTIONS = 40
FINISH_WINDOW = 6
OBJECTIVE_PREFIX = '\nExperiment recovery objective (priority for this episode): '

@dataclass(frozen=True)
class BaselineConfig:
    variant: str = 'S1_P1_P3'
    seed: int = 42

    def __post_init__(self):
        if self.variant not in VARIANTS:
            raise ValueError(f'unsupported frozen variant: {self.variant}')

    @property
    def knowledge_enabled(self):
        return self.variant != 'S1'

    @property
    def finish_enabled(self):
        return self.variant == 'S1_P1_P3'
