# OCR設定UIの引き継ぎ資料

VRChatのチャット吹き出しを読み取って翻訳する機能（OCR）の**バックエンドは完成している**。
UIは作り直す前提で一度削除したので、この資料だけを見てフロント側を実装できるようにまとめた。

対象読者はフロントエンド担当者。バックエンドのコードを読まなくても実装できることを目指している。
内部の設計は [src-python/docs/details/ocr.md](../src-python/docs/details/ocr.md) を参照。

## 1. この機能は何をするか

VRChatの画面をキャプチャ → 吹き出しを検出（学習済みYOLOv8n）→ 文字を読む（PP-OCR）→
重複を除いて既存の翻訳パイプラインへ流す。出力先はメッセージログとSteamVRオーバーレイの2つ。
**OSCでVRChatへ送り返すことはしない**（他人の発言を自分のチャットボックスに流すのは不適切なため、初版で封印）。

## 2. 削除したもの / 残してあるもの

| | 状態 |
|---|---|
| `setting_box/ocr/Ocr.jsx`, `Ocr.module.scss` | **削除**（画面そのもの） |
| サイドバーの「OCR」タブ（`SidebarSection.jsx`） | **削除** |
| `SettingBox.jsx` の `case "ocr"`、`setting_box/index.js` の export | **削除** |
| `SETTINGS_ARRAY` の `Category: "Ocr"` 7件 | **残した** |
| `useOcr()` フック（`logics/configs/index.js`） | **残した** |
| ロケールの `config_page.ocr.*`（5言語） | **残した** |
| メッセージログのOCRバッジ（`MessageContainer.jsx` の `is_ocr_message`） | **残した** |

`SETTINGS_ARRAY` を残したのは、ここを消すとバックエンドが初期化時に送る
`/get/data/ocr_*` が「未知のエンドポイント」になり、起動のたびに `console.error` が出るため。
UIの構成に合わせて自由に組み替えてよいが、**エンドポイント名との対応は保つこと**。

ロケールの文言は現状の仕様に合わせて書いてあるので、そのまま使っても書き直してもよい。

## 3. バックエンドとフロントの受け渡し

### 3-1. 起動時に一括で届く（7件）

他の設定とまとめて `/run/initialization_complete` に同梱される。個別に取りに行く必要はない。

| キー | 型 | 既定値 |
|---|---|---|
| `/get/data/ocr_capture` | bool | 常に `false`（保存されない。後述） |
| `/get/data/selectable_ocr_source_languages` | string[] | 読み取り言語の選択肢。3-5を参照 |
| `/get/data/ocr_source_language` | string | `"auto"` |
| `/get/data/ocr_window_title` | string | `"VRChat"` |
| `/get/data/ocr_poll_interval_ms` | int | `750` |
| `/get/data/ocr_min_confidence` | float | `0.85` |
| `/get/data/ocr_bubble_min_text_length` | int | `2` |

`ocr_capture` は `serialize=False` で保存されないため、**起動時は必ず `false`**。
OCRが勝手に始まることはなく、毎回ユーザーがONにする。

### 3-2. バックエンドから随時pushされる（2件）

| エンドポイント | 中身 | 現在の受け手 |
|---|---|---|
| `/run/enable_ocr_capture` | bool | `useOcr.updateFromBackendEnableOcrCapture` |
| `/run/transcription_ocr_message` | 下記 | `useMessage.addReceivedMessageLog` |

`/run/enable_ocr_capture` は**開始に失敗したときに `false` が飛んでくる**。UI側はこれを受けて
トグルを戻す（現在の実装もそうなっている）。成功時には飛ばない。

OCR結果のペイロード:

```json
{
  "id": "transcription-ocr-<segment_id>",
  "source": "ocr",
  "original":     { "message": "読み取った文", "transliteration": [] },
  "translations": [ { "message": "翻訳文", "transliteration": [] } ]
}
```

- `transliteration` は読み取った言語が日本語のとき入る（スピーカー受信と同じ扱い）。
  それ以外は空配列
- `translations` は翻訳が無効なら空配列
- `source: "ocr"` でマイク/スピーカー由来と区別できる（`MessageContainer.jsx` はこれでバッジを出している）

### 3-3. OCR経由で発火しうる共通のpush

OCR専用ではなく、マイク/スピーカーと共通の経路。OCRで読んだ文が引き金になることがある。

| エンドポイント | いつ |
|---|---|
| `word_filter` | ワードフィルタに引っかかった（この文はログに出ない） |
| `error_translation_engine` | 翻訳エンジンの制限に到達 |
| `error_translation_speaker_vram_overflow` ＋ `enable_translation(false)` | VRAM不足で翻訳を自動停止 |

### 3-4. フロントから叩けるもの

`useOcr()` が `SETTINGS_ARRAY` から自動生成する。項目名の付き方は次のとおり。

```
currentOcrSourceLanguage       状態（初期値は起動時のペイロード）
getOcrSourceLanguage()         /get/data/ocr_source_language を再取得
setOcrSourceLanguage(value)    /set/data/ocr_source_language
toggleEnableOcrCapture()       /set/enable/ocr_capture または /set/disable/ocr_capture
```

設定の値域と、範囲外を送ったときの挙動:

| エンドポイント | 型 | 値域 | 範囲外を送ると |
|---|---|---|---|
| `/set/data/ocr_source_language` | str | 3-5の選択肢のみ | **400** と現在値が返る（変更しない） |
| `/set/data/ocr_window_title` | str | 空文字は不可 | **400** と現在値が返る |
| `/set/data/ocr_poll_interval_ms` | int | 100〜5000 | クランプした値が返る |
| `/set/data/ocr_min_confidence` | float | 0.1〜0.99 | クランプした値が返る |
| `/set/data/ocr_bubble_min_text_length` | int | 1〜50 | クランプした値が返る |

**setの返却値で表示を更新すること。** 送った値がそのまま採用されるとは限らない
（例: `ocr_poll_interval_ms` に10000を送ると5000が返る）。

### 3-5. 読み取り言語の選択肢

`/get/data/selectable_ocr_source_languages` が配列で返す。**ハードコードしないこと**
（対応言語はモデル次第で変わる）。現在の内容:

```
["auto", "Arabic", "Hindi", "Korean", "Russian", "Thai", "Ukrainian"]
```

- `auto` … 日本語・英語・中国語（簡体/繁体）＋ラテン文字系40言語を**1つのモデルで自動認識**する。
  日本語話者の通常利用はこれで足りる
- それ以外 … 上記のモデルに含まれない文字体系。選ぶとモデルごと切り替わる
- 選択肢に「Japanese」等が無いのは、それらが `auto` と同じモデルで読めるため。
  設定として保存されている古い言語名（`Japanese` など）は `auto` と同じ扱いになる
- **アラビア語は現状精度が低い**（他言語より明確に劣る）。UIで期待値を下げる表現があるとよい

## 4. 設定変更のタイミング

**すべての設定はOCRを実行したまま変更でき、次の処理周期から反映される。** OFF→ONは不要。

- 言語を変えるとモデルを切り替える（一度使った組み合わせは即座に切り替わる）
- ウィンドウタイトルを変えるとキャプチャを開き直す
- 間隔・しきい値・最小文字数は値を差し替えるだけ

## 5. UIで必要な要素

1. **OCRのON/OFF**（トグル）。開始失敗時は `/run/enable_ocr_capture` で `false` が飛んでくる
2. **読み取り言語**（選択肢は 3-5 のとおりバックエンドから取得）。既定は `auto`
3. **対象ウィンドウ**（テキスト入力）。通常は変更不要
4. **取得間隔 / 信頼度のしきい値 / 最小文字数**（スライダー）。上級者向けにまとめてよい

初期状態で全部を並べる必要はない。1と2が主役で、3〜4は折りたたみでも困らない。

## 6. 実装時に知っておくとよいこと

- **処理は重い**。1回の処理周期で1〜2.6秒かかることがある（吹き出し1件あたり約0.8秒、CPU推論）。
  取得間隔を短くしても速くはならない。「反応が遅い」ことを前提にした見せ方が要る
- **GPUは使わない**。以前あったGPU設定は廃止した（onnxruntimeのGPU版は音声認識側と共存できないため）
- **同じ文は再配送しない**。画面から消えて30秒経つまで覚えている（内部の定数。設定にはしていない）
- **改行は完全には復元できない**。VRChatは送信者の改行と折り返しを同じように描画するため、
  文末記号のない改行は繋がって出る。仕様として受け入れている
- 開始に失敗した理由、1周期ごとの内訳（フレーム取得/吹き出し検出/OCR/配送の件数）は
  バックエンドのログに30秒ごとに出る。UIに出す価値があるかは要検討

## 7. 改善したい点（UI側で拾えると嬉しい）

- **開始失敗の理由が伝わらない**。今はトグルが黙って戻るだけ。エラーコードを返す仕組みを
  バックエンドに足せるので、UIで出したい形式があれば合わせる
- **初回の待ち時間**。モデルの読み込みで最初の1回だけ数百msかかる。進捗表示は未実装
- **VRChatが起動していないときの扱い**。現状はフレームが取れないまま静かに待ち続ける
