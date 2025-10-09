# CHANGELOG

## 2025-10-09 — 型チェック整備と安全性向上

- 修正: `controller.py`
	- `Controller.chatMessage` の戻り値注釈を `dict` に明示（関数は JSON 系の応答オブジェクトを返します）。
	- `Controller.checkSoftwareUpdated` が実際に応答を返すように `return` を追加。

- 修正: `model.py`
	- `startCheckMicEnergy` / `startCheckSpeakerEnergy` のコールバック引数を Optional に変更し、呼び出し前に `callable` チェックを追加。これにより None を渡しても安全に扱えるようになりました。
	- `convertMessageToTransliteration` の返り値を常に list に統一。hiragana/romaji が False の場合は空リストを返します。
	- `createOverlayImageLargeLog` 等の Overlay 作成関数で `target_language` を dict で受けた場合に内部で言語リストへ正規化する挙動を明確化。

- 目的: mypy の型チェックの警告/エラーを削減し、ランタイムでの None 呼び出しによるクラッシュを防止するための低リスクな変更です。

- 注記:
	- 追加で `types-requests` をプロジェクト仮想環境にインストールし、mypy の外部型スタブ不足を解消しました。
	- 本チェンジは内部の型注釈とガードを中心としており、動作ロジックの大きな変更は行っていません。動作確認は mypy（型チェック）と ruff（lint）を通過したことをもって行っています。

## 1.0.0 (initial)
- 初回ドキュメント作成: ソースコードに基づく仕様書 / 詳細設計書を docs 配下に追加。
- 対象: utils, model, controller, device_manager, config, translation, transcription, overlay, websocket, osc, transliteration, watchdog

今後の作業候補:
- requirements.txt の自動生成とテストスイート追加
- ドキュメントの API サンプル（リクエスト/レスポンス）追加
- UML 図/シーケンス図の画像化
