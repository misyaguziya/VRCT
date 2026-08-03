"""
テレメトリ状態管理
- enable/disable フラグ
- 日次デデュープを永続 JSON で管理（app_started と error）
"""
import json
import os
from datetime import date
from threading import Lock
from typing import Optional


def _today() -> str:
    return date.today().isoformat()


class TelemetryState:
    """テレメトリ有効/無効と、日次デデュープ用の永続状態を管理する。

    永続ファイルのスキーマ:
        {
            "last_app_started_date": "YYYY-MM-DD",
            "errors_sent": {"YYYY-MM-DD": ["ERROR_CODE_1", ...]}
        }
    書き込み時に当日以外のエントリを掃除する。
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._enabled = True  # デフォルト有効
        self._storage_path = storage_path
        self._lock = Lock()
        self._data = self._load()

    def _load(self) -> dict:
        if not self._storage_path or not os.path.exists(self._storage_path):
            return {"last_app_started_date": None, "errors_sent": {}}
        try:
            with open(self._storage_path, "r", encoding="utf-8") as fp:
                loaded = json.load(fp)
            if not isinstance(loaded, dict):
                raise ValueError("telemetry state root is not a dict")
            return {
                "last_app_started_date": loaded.get("last_app_started_date"),
                "errors_sent": loaded.get("errors_sent") or {},
            }
        except Exception:
            # 破損時は初期化。呼び出し元に例外を伝播させない。
            return {"last_app_started_date": None, "errors_sent": {}}

    def _save_locked(self):
        if not self._storage_path:
            return
        try:
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            with open(self._storage_path, "w", encoding="utf-8") as fp:
                json.dump(self._data, fp, ensure_ascii=False, indent=2)
        except Exception:
            # 書き込み失敗は握りつぶし（テレメトリでアプリを止めない）
            pass

    def _prune_locked(self):
        """当日以外の errors_sent エントリを削除。"""
        today = _today()
        errors_sent = self._data.get("errors_sent") or {}
        self._data["errors_sent"] = {
            k: v for k, v in errors_sent.items() if k == today
        }

    def set_storage_path(self, storage_path: str):
        """遅延で保存先を差し替える（config 初期化順序への対応）。"""
        with self._lock:
            self._storage_path = storage_path
            self._data = self._load()

    def set_enabled(self, value: bool):
        with self._lock:
            self._enabled = bool(value)

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def should_send_app_started_today(self) -> bool:
        with self._lock:
            return self._data.get("last_app_started_date") != _today()

    def mark_app_started_sent_today(self):
        with self._lock:
            self._data["last_app_started_date"] = _today()
            self._prune_locked()
            self._save_locked()

    def should_send_error_today(self, error_code: str) -> bool:
        if not error_code:
            return False
        today = _today()
        with self._lock:
            errors_sent = self._data.get("errors_sent") or {}
            return error_code not in (errors_sent.get(today) or [])

    def mark_error_sent_today(self, error_code: str):
        if not error_code:
            return
        today = _today()
        with self._lock:
            errors_sent = self._data.get("errors_sent") or {}
            today_list = list(errors_sent.get(today) or [])
            if error_code not in today_list:
                today_list.append(error_code)
            self._data["errors_sent"] = {today: today_list}
            self._save_locked()

    def reset(self):
        """有効/無効フラグの実行時リセットのみ（永続データは保持）。"""
        # 永続データは削除しない。日次デデュープはプロセス終了後も維持したい。
        pass

    def get_debug_info(self) -> dict:
        with self._lock:
            return {
                "enabled": self._enabled,
                "storage_path": self._storage_path,
                "last_app_started_date": self._data.get("last_app_started_date"),
                "errors_sent": dict(self._data.get("errors_sent") or {}),
            }
