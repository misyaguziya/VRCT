VRCT Gemini Annotator — Windows x64
==================================

収集ツールのPNGとJSON一式から、Geminiでチャットボックスの仮ラベルを作り、
Label Studioで修正できるJSONを生成します。元画像は変更しません。
このexeの実行にPythonやVRCT本体は不要です。Gemini APIキーはご用意ください。
Label Studio本体は別途インストールします。静的JSON取り込みなのでML backendは不要です。

【まず使う】
1. ZIPを全展開し、書き込み可能な場所に置く。
2. VRCT-Gemini-Annotator.exeをダブルクリック。
3. 収集データのdataset_collectedフォルダを指定。
   セッション単位やunlabeledフォルダの指定も可能。PNGと同名JSONの両方が必要。
4. 抽出枚数を入力。Enterなら100枚、0なら全件。
   セッション・撮影run・取得方法を分散させ、seed=42で抽出する。
5. exe隣のannotation_jobsに作業フォルダが作られる。
   画像コピーのため追加のディスク容量が必要。最初は100枚を推奨。
6. 1を選ぶと未処理画像をGeminiへ送信。APIキーを非表示で入力する。
   Enterだけなら送信せず、作業フォルダの準備で終了する。
7. 完了時に表示されるexports内のSTART_HERE.txtに従ってLabel Studioへ取り込む。

APIキーはファイルに保存しません。環境変数GEMINI_API_KEYも使用できます。
画像はGemini APIへ送信され、料金・データ利用条件は契約プランに従います。
モデル既定はgemini-2.5-flash。無料15RPM等の固定quotaを仮定していません。
間隔は6秒以上（応答完了後から計測）。429/一部5xxだけ最大2回自動再試行します。
タイムアウト等は結果不明とし、自動再試行しません。再試行で重複課金が生じる可能性があります。
料金は画像・本文・思考/出力トークン次第です。statusで報告されたusageを確認できます。
max_output_tokens=8192、thinkingはモデルの既定設定。定額の枚数料金ではありません。

【中断・再開】
Ctrl+Cで中断できます。再度exeを起動し、前回の作業フォルダのパスを指定してください。
1は未処理だけ、2は失敗・結果不明も再試行します。成功済み画像は再送しません。
画像のSHA-256とモデル・prompt・schemaの一致を確認してから再開します。
同じ作業フォルダを複数プロセスで同時に処理することはできません。
収集元に画像が追加されても作業フォルダは増えません。別の作業フォルダを準備してください。
別モデルを比較する場合も新しい作業フォルダを使います。

【状態の意味】
detected: 枠を検出したが未確認
no_detection: Geminiが見つけなかった。背景画像と確定した意味ではない
invalid_response: JSON/座標/クラス不正、応答打ち切り等
api_error: HTTPエラー。設定/認証エラーやquota上限では残りの処理を停止
unknown: 中断・タイムアウト等で結果不明。課金されていない保証はない
pending: まだ処理していない

全画像をLabel Studioへ渡します。未検出・失敗画像も確認し、見落としの枠を追加してください。
「チャット背景板と文字を含めた全体」を1枠とし、名札・看板・メニューは除外します。
複数枠に対応。枠を回転させず、画像に平行な矩形を使用します。
不正な座標を黙って補正することはありません。

【Label Studio導入：Python 3.11を用意したPCのPowerShellで初回のみ】
  py -3.11 -m venv .venv-label-studio
  .\.venv-label-studio\Scripts\python.exe -m pip install "label-studio==1.23.0"

次に、exports内のSTART_HERE.txtの環境変数2行を実行し、起動コマンドを次に置き換える:
  .\.venv-label-studio\Scripts\label-studio.exe start

新しいprojectを作り、label_config.xmlをLabeling Interfaceに設定する。
Local Filesの保存先とDOCUMENT_ROOTはSTART_HERE.txtに具体的なパスを記載しています。
tasks.jsonを1度だけImportする。再出力したJSONを同じprojectへ再importしないでください。
予測自体は読取専用です。Show predictions to annotatorsを有効にし、
予測をコピーしたannotationを修正してSubmitします。
全画像を確認・SubmitしてからYOLOでExport。未確認/Skip画像を負例にしないでください。
確認済みの枠なし画像は負例として保持し、classes.txtと画像名の対応も確認します。
同じ撮影runの近い画像は学習/検証の別グループへ分けないでください。

【CLI：exeのフォルダでPowerShellから実行】
  .\VRCT-Gemini-Annotator.exe prepare "D:\captures" --out "D:\annotation-job" --limit 100
  .\VRCT-Gemini-Annotator.exe annotate "D:\annotation-job" --limit 100
  .\VRCT-Gemini-Annotator.exe annotate "D:\annotation-job" --retry-failed --limit 20
  .\VRCT-Gemini-Annotator.exe status "D:\annotation-job"
  .\VRCT-Gemini-Annotator.exe export "D:\annotation-job"
  .\VRCT-Gemini-Annotator.exe check

CLIのannotateは環境変数GEMINI_API_KEYが必要です。キーをコマンド引数に書かないでください。
prepareには--seed/--model、annotateには--interval/--retriesがあります。
prepare/annotateの--limit 0は全件。準備と1回の処理上限は別です。
prepare/export/status/checkは画像を送信しません。
終了コード: 0=成功、1=設定等のエラー、2=annotate後も失敗/未処理あり、130=中断。

【保存物】
manifest.json: 入力との対応、撮影metadata、画像SHA-256、抽出条件
images/: 変更しない画像コピー
prompt.txt / response_schema.json: 使用した検出指示と形式の記録（編集しても設定は変わりません）
attempts/: API試行ごとの開始・結果、生の応答、usage
results/: 各画像の最新状態
exports/<日時>/: Label Studio用tasks.json、label_config.xml、summary.json、START_HERE.txt

exportsは毎回新規作成し、以前の出力とLabel Studioの人手修正データを上書きしません。
作業フォルダは全体を保管してください。移動したらDOCUMENT_ROOTも変更します。
配布時はこのZIPとlicensesだけを渡し、annotation_jobsを混ぜないでください。
このexeは未署名です。Python未導入の別PC、実Geminiでの精度、Label Studio画面での
編集・YOLO出力は別途実データで確認してください。

仕様参照（2026-09-14確認）:
https://ai.google.dev/gemini-api/docs/image-understanding#object-detection
https://ai.google.dev/gemini-api/docs/structured-output
https://ai.google.dev/gemini-api/docs/rate-limits
https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash
https://ai.google.dev/gemini-api/terms#how-google-uses-your-data
https://labelstud.io/guide/storage_local
https://labelstud.io/guide/predictions
https://labelstud.io/guide/export
