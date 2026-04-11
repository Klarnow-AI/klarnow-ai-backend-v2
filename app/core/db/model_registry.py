"""Load all SQLAlchemy model modules so Base.metadata is complete in every process."""

from importlib import import_module

_MODEL_MODULES = (
    "app.modules.agents.models",
    "app.modules.brand_os.models",
    "app.modules.builder.models",
    "app.modules.creative.models",
    "app.modules.packs.models",
    "app.modules.projects.models",
    "app.modules.waitlist.models",
)

_models_loaded = False


def load_model_metadata() -> None:
    """Import every ORM model module once so string ForeignKeys resolve reliably."""

    global _models_loaded
    if _models_loaded:
        return

    for module_path in _MODEL_MODULES:
        import_module(module_path)

    _models_loaded = True
