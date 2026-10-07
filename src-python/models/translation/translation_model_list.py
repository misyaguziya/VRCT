import time
from typing import List, Optional

# 取得したモデル一覧を、setModel の確認に使い回す時間 (秒)。起動時は
# 「getModelList() で一覧を取る → 選んだモデルを setModel() で確かめる」と続けて呼ぶため、
# 2回目の取得 (ネットワーク) を省ける。UI の更新ボタンなど、あとから呼ぶときは古くなるので取り直す。
_RECENT_SEC = 30.0


class RecentModelList:
    """モデル一覧を返すクライアント (getModelList を持つ) の共通部分。

    getModelList() は取得した一覧を `_remember()` で返す。setModel() は、直近に取得した一覧が
    あればそれで確かめ、無ければ取得し直す。
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

    def setModel(self, model: str) -> bool:
        models = self._recentModels()
        if models is None:
            models = self.getModelList()
        if model in models:
            self.model = model
            return True
        return False
