import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC_PYTHON_DIR = os.path.dirname(os.path.abspath(__file__))
_MARKER = '{"marker": "should survive import"}'


class ManualDiagnosticScriptsDoNotDeleteConfigOnImportTests(unittest.TestCase):
    """Regression coverage for item 15: test_endpoints.py / test_client.py
    match pytest's test_*.py collection glob by naming coincidence, but
    are standalone, manually-run CLI diagnostic tools (see
    docs/test_endpoints.md and docs/test_client.md), not pytest suites.

    Merely importing either file (which is all pytest collection does,
    including when the file is passed explicitly on the command line --
    conftest.py's collect_ignore only covers directory-traversal
    discovery, not an explicitly named path) must not delete config.json
    in the current working directory or trigger heavy real-app
    initialization. That must only happen when the script is executed
    directly (`python test_endpoints.py` / `python test_client.py`,
    i.e. under __main__), which is their documented usage.
    """

    def _assert_import_is_side_effect_free(self, module_name: str) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(_MARKER, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f"import sys; sys.path.insert(0, {_SRC_PYTHON_DIR!r}); import {module_name}",
                ],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(
                config_path.exists(),
                f"config.json was deleted merely by importing {module_name}",
            )
            self.assertEqual(config_path.read_text(encoding="utf-8"), _MARKER)

    def test_importing_test_endpoints_does_not_delete_config_json(self) -> None:
        self._assert_import_is_side_effect_free("test_endpoints")

    def test_importing_test_client_does_not_delete_config_json(self) -> None:
        self._assert_import_is_side_effect_free("test_client")


if __name__ == "__main__":
    unittest.main()
