# 収集画像からGeminiの仮アノテーションを作る

前提はDataset Collectorが生成した `session/unlabeled/*.png` と同名のJSON一式。
`positive/negative/` も入力可能だが、撮影時の分類を正解bboxとしては扱わない。
操作の詳細は [配布README](../tools/gemini_annotator/README.txt) を参照。

## 使い始める

`tool-dist/VRCT-Gemini-Annotator-windows-x64.zip` を展開し、exeを起動する。
画像フォルダ、抽出枚数（既定100枚）を入力すると、exe隣の `annotation_jobs/` に
独立した作業フォルダを作る。送信する場合は1を選びAPIキーを入力する。
Label Studioは別途導入し、`exports/<日時>/START_HERE.txt` の手順で取り込む。

Pythonからの使用例:

```powershell
.\.venv-annotator\Scripts\python.exe -X utf8 tools\gemini_bbox_labeler.py prepare 'D:\captures' --out 'D:\annotation-job' --limit 100
# GEMINI_API_KEYを環境変数で設定してから実行。キーは保存・表示しない。
.\.venv-annotator\Scripts\python.exe -X utf8 tools\gemini_bbox_labeler.py annotate 'D:\annotation-job' --limit 100
.\.venv-annotator\Scripts\python.exe -X utf8 tools\gemini_bbox_labeler.py status 'D:\annotation-job'
```

旧CLIの `input_dir --out` による即YOLO出力は廃止した。新しいコマンドは
`prepare/annotate/export/status/check`。本番VRCTのendpointや収集ツールは変更していない。

## 設計とデータの境界

1. **prepare（オフライン）**: 再帰走査で収集PNG/JSONを列挙し、session/run/backendを分散して
   seed付き抽出。画像名・寸法・PNG形式を照合し、入力外の新規jobへコピーする。
   manifestの確定前に失敗したjobは公開しない。元画像・metadataは変更しない。
2. **annotate（Geminiへの送信）**: job画像とpolicyのSHA-256を照合してから、未処理を順次送信する。
   モデル既定は `gemini-2.5-flash`。公式SDKのJSON Schemaで全bboxを受け、整数4要素、
   0..1000、正の面積、クラス、重複をローカル検証する。途中で切れた応答も不採用。
3. **export（オフライン）**: すべての画像に対しLabel Studio tasksを出力。成功時だけ
   `predictions`を付け、`annotations`は作らない。空予測、失敗、未処理も人手で確認する。
   各出力は日時付きの新規フォルダ。Label StudioのDBや人手の成果物へ書き戻さない。
4. **人手確定とYOLO**: Label Studioで予測をannotationへコピーして修正・Submit。
   全画像を確認してから標準YOLO出力を使う。未確認やSkipを負例にせず、確認済みの枠なし画像を
   保持する。class 0=`chat_box`と画像対応を検査し、同一撮影runが学習/評価にまたがらないよう分割する。

状態は `detected/no_detection/api_error/invalid_response/unknown/pending`。
`no_detection`は検出器の判断であり、正解負例ではない。
API呼び出し前にunknownを保存し、完了後に応答・usage・結果を原子的に置き換える。
試行履歴を残し、再開では成功を再送しない。失敗/unknownは`--retry-failed`で明示的に再試行。
通信完了とファイル保存を一体化できないため、中断・タイムアウトの重複課金は保証できない。
OSファイルロックで同じjobの同時操作を防ぐ。プロセス異常終了でもOSがロックを解放する。

6秒の間隔はquota保証ではない。429/500/502/503/504のみ最大2回自動再試行し、
Retry-Afterがあれば尊重する。設定・認証エラー、再試行後も429なら処理全体を止める。
SDK内部の自動再試行は1試行に制限。120秒の要求timeout。
料金を固定値で推定せず、statusで全履歴の報告usageを表示する（未応答分の使用量は不明）。

画像は元の寸法を維持し、Geminiの0..1000をLabel Studioの左上xywh百分率へ変換する。
Label Studioにコピー先jobをLocal Filesとして登録するため、外部画像ホスティングは不要。
同じprojectへのtasks再importは更新として扱わず、新規projectを使用する。

## 配布ビルドと検証

既存 `.venv` の依存を変更せず、専用の `.venv-annotator` に
`requirements-gemini-annotator.txt` を導入してビルドする。既存アプリの環境には
同じimport名を置き換える依存やoptionalパッケージがあり、流用すると通知と実物がずれる。
別のクリーン環境を使う場合は `VRCT_ANNOTATOR_PYTHON` にpython.exeを指定する。
Label Studioは独立venvに `label-studio==1.23.0` を導入する（このexeに同梱しない）。

```powershell
py -3.11 -m venv .venv-annotator
.\.venv-annotator\Scripts\python.exe -m pip install -r requirements-gemini-annotator.txt
.\bat\build_gemini_annotator.bat
.\.venv\Scripts\python.exe -m pytest -q src-python\test_gemini_bbox_labeler.py
.\.venv\Scripts\python.exe -m ruff check tools\annotation_job.py tools\gemini_bbox_labeler.py tools\build_gemini_annotator.py src-python\test_gemini_bbox_labeler.py
```

ビルドは新しいステージからZIPを作り、既存jobを巻き込まない。exeとREADME、依存ライセンス、
BUILD-INFO、ZIP SHA-256を生成する。実キーを渡さずSDK初期化と合成PNGのprepare/exportを検査する。
API通信テストはHTTPXのメモリ内transportを使い、実Geminiへは接続しない。
画像の内容を検出する精度、実際のquota/料金、Label Studio画面での最終確認は実データの試行で測る。

2026-09-14の検証結果:

- 対象pytest 31件成功、対象4ファイルのruff成功。独立レビューの指摘は解消済み。
- 専用環境からexe/ZIPビルド成功。ZIPのCRC・SHA-256・exeハッシュ・ライセンス・同梱物を独立確認。
- ZIPを日本語・空白入りの一時パスに展開し、WindowsのみのPATH、APIキーなしで
  `check/prepare/status/export` が終了コード0。元画像のハッシュを維持し、API試行記録なし。
- 引数なしexeの対話操作でも、合成画像の取り込みから「準備だけで終了」まで成功。
- 実Gemini API、実画像の検出精度、Label Studioの画面操作・YOLO出力、Python未導入の別PCは未検証。

## 確認した公式仕様

- [Gemini画像検出](https://ai.google.dev/gemini-api/docs/image-understanding#object-detection)
- [構造化出力](https://ai.google.dev/gemini-api/docs/structured-output)
- [レート制限](https://ai.google.dev/gemini-api/docs/rate-limits)
- [モデル提供状況](https://ai.google.dev/gemini-api/docs/deprecations)
- [料金](https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash)・[データ利用条件](https://ai.google.dev/gemini-api/terms#how-google-uses-your-data)
- [Label Studio Local Files](https://labelstud.io/guide/storage_local)・[予測取り込み](https://labelstud.io/guide/predictions)・[出力](https://labelstud.io/guide/export)
