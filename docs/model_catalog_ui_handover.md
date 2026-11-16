# モデル（重み）の管理 UI の引き継ぎ資料

文字起こし（Whisper）と翻訳（CTranslate2）のモデルを「入れる・止める・消す・取得元を変える」機能の
**バックエンドはできている**（2026-11-16、P4）。UI はまだ無い。この資料だけでフロント側を作れるようにまとめた。

対象読者はフロントエンド担当者。設計の経緯は `docs/rust_next_design_2026-11-15.md` の P4 節。

## 1. この機能は何をするか

- 入れられるモデルは **VRCT が確かめたモデルの一覧（カタログ）だけ**。今は従来どおりの 14 個
  （Whisper 9・CTranslate2 5）。カタログは exe に埋め込まれていて、モデルごとにリポジトリの commit・
  ファイルの大きさ・SHA-256 が決まっている。
- **自由な検索は無い**（Hugging Face のモデルを名前で探して入れる、はやめた）。理由: 翻訳の言語表と
  トークナイザーがモデルの系統ごとに要り、文字起こしも英語専用モデルなどは黙って動きが変わるため。
  `docs/rust_next_ui_design_2026-11-15.html` の「検索」と `*_WEIGHT_TYPE` の `hub:…` の値は**廃止**。
- 取得は途中から再開でき（`.part` が残る）、取り終えたファイルは SHA-256 を照合してから使う。
- ID・設定値・フォルダー名・push の `weight_type` は今と同じ（`base`、`nllb-200-distilled-600M-ct2-int8` など）。

## 2. 起動時に一括で届く（3 件、新規）

他の設定とまとめて `/run/initialization_complete` に入る。受け手が無いと起動のたびに
「未知のエンドポイント」で `console.error` が出るので、今は `src-ui/logics/useReceiveRoutes.js` の
「Not Implemented」欄に `ns: null` の行を 3 つ置いてある。**UI を実装するときは、この 3 行を本物の受け手に置き換える。**

| キー | 型 | 中身 |
|---|---|---|
| `/get/data/model_catalog` | object[] | 入れられるモデル（下記）。並びは表示順に使ってよい |
| `/get/data/model_list` | object[] | このPCでの状態（下記）。カタログと同じ並び |
| `/get/data/hf_endpoint` | string | 取得元。既定 `"https://huggingface.co"` |

`model_catalog` の 1 件:

```json
{"id": "nllb-200-distilled-600M-ct2-int8", "family": "nllb", "size": 664682766,
 "license": "CC-BY-NC-4.0", "repo": "JustFrederik/nllb-200-distilled-600M-ct2-int8"}
```

- `family`: `whisper`（文字起こし）/ `m2m100` / `nllb`（翻訳）。`whisper` 以外は翻訳のモデル
- `size`: 取得する全ファイルのバイト数（翻訳はトークナイザー込み）。`src-ui/logics/ui_configs.js` の
  `ctranslate2_weight_type_status` / `whisper_weight_type_status` に手で書いてある `capacity`（"600MB" など）は、
  これから作れる（固定の表を消せる）
- `license`: NLLB の 3 つは **CC-BY-NC-4.0（非商用）**。それ以外は MIT。表示だけ（同意は求めない）

`model_list` の 1 件:

```json
{"id": "base", "family": "whisper", "bytes": 147883199, "installed": true,
 "partial": false, "in_use": true, "downloading": false}
```

| キー | 意味 |
|---|---|
| `bytes` | フォルダーの中のファイルの合計（途中の `.part` も含む）。入っていなければ 0 |
| `installed` | 読み込めると確かめ済み（`SELECTABLE_*_WEIGHT_TYPE_DICT` の値と同じ） |
| `partial` | 途中まで取った `.part` がある（もう一度「入れる」と続きから） |
| `in_use` | 今選ばれている（`selected_whisper_weight_type` / `selected_ctranslate2_weight_type`） |
| `downloading` | 取得中 |

`model_list` は自動では送られない。取得の完了・中止・削除の後や、画面を開いたときに
`/get/data/model_list` を取り直す（削除の応答にも入っている）。

## 3. push（キーは変わらない）

今の 6 つのまま。中身の意味が少し変わった。

| エンドポイント | 中身 | 変わった点 |
|---|---|---|
| `/run/download_progress_whisper_weight` `/run/download_progress_ctranslate2_weight` | `{"weight_type": id, "progress": 0〜1}` | **モデル全体**（翻訳はトークナイザー込み、再開した分も最初から数える）。前は model.bin だけ |
| `/run/downloaded_whisper_weight` `/run/downloaded_ctranslate2_weight` | id | 既に入っているモデルを「入れる」と、翻訳でもすぐこれが届く |
| `/run/error_whisper_weight` `/run/error_ctranslate2_weight` | エラー応答（`WEIGHT_*_DOWNLOAD`、`data: null`） | `details` に `{"weight_type": id, "reason": …}` |

`reason`:

| 値 | 意味 | UI での案 |
|---|---|---|
| `network` | 取れなかった（通信・サーバー・ファイルの書き込み） | 「もう一度」。`.part` は残るので続きから |
| `sha256` | 取れたが中身がカタログと違う（壊れた・差し替えられた）。一度に取れたファイルが違えば取り直さない | 取得元（ミラー）を疑う文言 |
| `disk_space` | 空き容量が足りない（始めていない） | 必要な大きさ（カタログの `size`）を添える |
| （無い） | 揃ったのに読み込めなかった | 一般的な失敗 |

- progress は戻ることがある: 途中から再開しようとしてサーバーが応じなかったとき（Range の無視・416）は、
  そのファイルを 0 から取り直す。表示は戻った値をそのまま出してよい。
- progress が 1.0 になった後、大きなモデル（3GB 級）は照合と読み込みの確認で数秒〜十数秒止まって見える。
  そのあとで `downloaded_*` か `error_*` が届く。
- **中止したときは何も push しない**。

## 4. フロントから叩けるもの

| エンドポイント | 送るもの | 応答 |
|---|---|---|
| `/run/download_whisper_weight` `/run/download_ctranslate2_weight`（既存） | id | `true`（始めた。結果は push）。同じモデルが取得中ならそれを続ける（中止を頼んだ後でも取り消して続ける） |
| `/run/cancel_weight_download`（新） | id | `true`（止めた）/ `false`（動いていない） |
| `/delete/data/model`（新） | id | 成功: 更新後の `model_list`。失敗: 下のエラー（400） |
| `/get/data/model_list`（新） | なし | 2 章の `model_list` |
| `/get/data/hf_endpoint` / `/set/data/hf_endpoint`（新） | 文字列 | 保存した値 |

### 中止

- 次のデータの受け取りで止まる。`.part` は残り、もう一度「入れる」と続きから。
- 行き違いで、`true` が返った後に `downloaded_*` が届くことがある（ちょうど終わったとき）。届いたらそれを正とする。
- 中止の直後に同じモデルを「入れる」と、中止は取り消され、その取得が続いて終わりの push が届く。
- アプリの終了時も取得は止まる（`.part` は残る）。起動時の自動取得は、中止されたモデルを取り直さない。

### 削除

| error_code | 意味 | UI での案 |
|---|---|---|
| `WEIGHT_UNKNOWN` | カタログに無い id | 通常は起きない |
| `WEIGHT_IN_USE` | 選択中か取得中 | 「先に別のモデルを選んでください」/ 取得中は先に中止させる |
| `WEIGHT_DELETE_FAILED` | 消せないファイルがあった（他のプロセスが開いている等）。`details.error` に OS のエラー。一部は消えているので `installed` は false になる | 「もう一度」。入れ直しが要る |

- 消せるのは選んでいないモデルだけ。消すと `installed` が false になる。入っていないモデルの削除も成功扱い。
- パスは送らない（id だけ）。
- 削除と選択の行き違い: 削除の要求中にそのモデルを選ぶと、選んだモデルが消えることがある。削除の応答が返るまで、
  その行の選択とボタンを止める。

### 取得元（HF_ENDPOINT）

- `https://` で始まり、ホスト（とポート）だけのもの。パス・`?`・`#`・ユーザー名は不可。
  保存するのは読み直した正規の形（前後の空白・末尾の `/` なし、ホストは小文字、443 は省く）。応答の値を表示に使う。
- それ以外は `VALIDATION_CONFIG_VALUE_INVALID`（400、`data` は送った値）で、値は変わらない。
- `hf-mirror.com` などのミラーを「プリセット」として出すかは UI の判断（中国からの利用者向け、#124 と同じ層）。
  ミラーが違うファイルを返しても SHA-256 の照合で弾かれる（`reason: "sha256"`）。

## 5. UI で必要な要素（案）

1. モデルの一覧（文字起こし・翻訳で分ける）。名前・大きさ（`size`）・ライセンス・状態（入っている / 途中 / 使用中 / 取得中）
2. 行ごとのボタン: 入れる（途中なら「続きから」）・中止・削除（使用中は押せない）
3. 取得中の進み具合（push の `progress`）
4. 取得元の入力（上級者向け。折りたたみでよい）

文言キーの案（`config_page.models.*`）: `title`、`size`、`license`、`non_commercial`、`install`、`resume`、`cancel`、
`delete`、`in_use`、`downloading`、`partial`、`error_network`、`error_sha256`、`error_disk_space`、
`error_in_use`、`hf_endpoint`、`hf_endpoint_invalid`。

## 6. 知っておくとよいこと

- 選択の endpoint（`/set/data/selected_*_weight_type`）と `SELECTABLE_*_WEIGHT_TYPE_LIST/DICT` は今のまま。カタログの id と同じ並び。
- 進み具合の push は 1% ごとか 0.5 秒ごと（今と同じ間引き）。
- 実機・実回線で未確認のこと: Hugging Face と hf-mirror.com からの実取得・途中で切って再開、プロキシ越し、
  3.3B の取得と照合の時間、ウイルス対策ソフトの下での名前の付け替え、空き容量不足の通知、
  選択を外した直後のモデルの削除。
