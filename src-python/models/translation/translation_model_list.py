import time
from typing import Callable, List, Optional

# 取得したモデル一覧を使い回す時間 (秒)。起動時は次の順に呼ぶため、同じ一覧を2回、3回と取りに行っていた:
#   setAuthKey() (認証で一覧を取る) → getModelList() (一覧を取る) → setModel() (選んだモデルを確かめる)
# 2回目以降のネットワークを省く。UI の更新ボタンなど、あとから呼ぶときは古くなるので取り直す。
_RECENT_SEC = 30.0


class RecentModelList:
    """モデル一覧を返すクライアント (getModelList を持つ) の共通部分。

    - getModelList() は取得した一覧を `_remember()` で返す。setModel() は、直近に取得した一覧が
      あればそれで確かめ、無ければ取得し直す。
    - 認証が一覧の取得を兼ねるクライアントは、setAuthKey() で `_rememberFromAuth()` に一覧を渡す。
      認証の直後の最初の getModelList() だけが、それを使う (1回きり)。更新ボタンなどのあとの呼び出しは
      取得し直す。
    """

    def _remember(self, models: List[str]) -> List[str]:
        # 取得に失敗した ([]) 一覧は覚えない。setModel が取り直せるように
        if models:
            self._recent_models = (time.monotonic(), list(models))
        return models

    def _recentModels(self) -> Optional[List[str]]:
        recent = getattr(self, "_recent_models", None)
        if recent is not None and time.monotonic() - recent[0] <= _RECENT_SEC:
            return recent[1]
        return None

    def _rememberFromAuth(self, build: Callable[[], List[str]]) -> None:
        """認証で受け取った応答から一覧を作って、1回きり使えるように覚える。

        一覧を作れなくても (想定外の応答など)、認証の結果は変えない。getModelList() が取り直す。
        """
        try:
            models = build()
        except Exception:
            return
        if models:
            self._auth_models = (time.monotonic(), list(models))

    def _takeAuthModels(self) -> Optional[List[str]]:
        auth_models = getattr(self, "_auth_models", None)
        self._auth_models = None
        if auth_models is not None and time.monotonic() - auth_models[0] <= _RECENT_SEC:
            return auth_models[1]
        return None

    def setModel(self, model: str) -> bool:
        models = self._recentModels()
        if models is None:
            models = self.getModelList()
        if model in models:
            self.model = model
            return True
        return False
