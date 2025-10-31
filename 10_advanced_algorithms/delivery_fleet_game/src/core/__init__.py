"""Core game logic package with lazy exports to avoid circular imports."""

__all__ = [
    "GameEngine",
    "Router",
    "RouteValidator",
    "DifficultySnapshot",
    "DemandTier",
    "create_difficulty_snapshot",
]

_LAZY_IMPORTS = {
    "GameEngine": ".engine",
    "Router": ".router",
    "RouteValidator": ".validator",
    "DifficultySnapshot": ".difficulty",
    "DemandTier": ".difficulty",
    "create_difficulty_snapshot": ".difficulty",
}


def __getattr__(name):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module 'src.core' has no attribute '{name}'")

    module_name = _LAZY_IMPORTS[name]
    from importlib import import_module

    module = import_module(module_name, __name__)
    attr = getattr(module, name)
    globals()[name] = attr
    return attr


def __dir__():
    return sorted(__all__)
