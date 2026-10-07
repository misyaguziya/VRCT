"""pytest collection configuration for src-python/test.

collect_ignore excludes files that match pytest's test_*.py discovery glob
by naming coincidence but are not pytest suites: standalone, manually-run
CLI diagnostic tools that talk to a real backend process/instance (see
docs/test_endpoints.md and docs/test_client.md). Both unconditionally
delete config.json in the current working directory on import, and
test_endpoints.py additionally imports mainloop's real main_instance --
merely collecting them (even though pytest cannot actually run their
__init__-having "test" classes) is enough to trigger those side effects
against whatever real config.json happens to be in the working directory.

Neither file is meant to run under pytest; both are still fully usable
the documented way (`python test/test_endpoints.py`, `python test/test_client.py`).
"""

collect_ignore = [
    "test/test_endpoints.py",
    "test/test_client.py",
]


# --- テストが開発者の実際の config.json を書き換えないようにする -------------------------
# `config` はシングルトンで、import 時に src-python/config.json を読む。テストが
# `config.AUTH_KEYS = ...` のように代入すると、保存 (saveConfigToFile) が同じ実際のファイルへ
# 書き込まれ、後始末が追いつかなかった値が残る。実際に、全テストを実行するたびに
# AUTH_KEYS (翻訳の API キー) がすべて None になり、開発中のアプリのキーが消えた。
# 読み込みは実際のファイルのまま (既存のテストが前提にしている) にして、保存先だけを
# このテストセッション限りの一時ファイルへ向ける。
import atexit
import shutil
import tempfile
from os import path as _os_path

from config import config as _config

_config_dir = tempfile.mkdtemp(prefix="vrct-test-config-")
atexit.register(shutil.rmtree, _config_dir, ignore_errors=True)
_config._PATH_CONFIG = _os_path.join(_config_dir, "config.json")

# process.log / error.log も同じ。ログのファイル名は実行時の作業ディレクトリからの相対で、init() が
# removeLog() で process.log を空にするため、テストを実行するたびに、開発中のアプリのログ (起動の
# 所要時間などの調査に使うもの) が消えて、テストの出力に置き換わっていた。
import logging

import utils as _utils

_utils.process_logger = _utils.setupLogger("process", _os_path.join(_config_dir, "process.log"), logging.INFO)
_utils.error_logger = _utils.setupLogger("error", _os_path.join(_config_dir, "error.log"), logging.ERROR)
# controller は `from utils import removeLog` で import 時に名前を取り込むので、その前に差し替える
_utils.removeLog = lambda: None
