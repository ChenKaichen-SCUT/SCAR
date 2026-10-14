"""Local agents coexist with the unchanged upstream agents package."""
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
