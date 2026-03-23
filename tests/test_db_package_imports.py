from __future__ import annotations

import os
import subprocess
import sys
import unittest


class DatabasePackageImportTests(unittest.TestCase):
    def test_importing_base_does_not_import_session_module(self) -> None:
        env = os.environ.copy()
        env.setdefault("DATABASE_URL", "sqlite:///./test-db-package-imports.db")
        env.setdefault("SECRET_KEY", "test-secret")
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import importlib, json, sys; "
                    "importlib.import_module('app.core.db.base'); "
                    "print(json.dumps('app.core.db.session' in sys.modules))"
                ),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.stdout.strip(), "false")


if __name__ == "__main__":
    unittest.main()
