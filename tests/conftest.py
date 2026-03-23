from __future__ import annotations

import os


# Several test modules import the FastAPI app at module import time.
# Seed a stable test-only secret before pytest collects those modules.
os.environ.setdefault("SECRET_KEY", "test-secret")
