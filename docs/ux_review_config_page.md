# VRCT 設定画面（Config ページ）UX レビュー

- **対象**: `src-ui/views/app/config_page/`（JSX 55 / SCSS 54 ファイル）、`src-ui/logics/configs/`、`locales/*.yml`
- **ブランチ**: `feature/beta-release-pipeline`（`89eb4337` 時点）
- **実施日**: 2026-08-27
- **方法**: 3 名のレビュアーが独立した観点でコードを読み、指摘を統合。

> **検証済み（2026-08-27）**: 定量データ・コントラスト比・バグ 3 件を含む主要な指摘を実コードで再検証しました。コントラスト比 7 組はすべて小数点 2 桁まで一致、i18n のキー数・欠落・空値も完全一致。誤りが 2 点あり修正済みです（`:focus` の件数と `--config_page_sidebar_width` の参照有無。いずれも結論は変わりません）。

| レビュアー | 観点 |
|---|---|
| **A** | 情報アーキテクチャ / ナビゲーション |
| **B** | オンボーディング / タスク完遂 / フィードバック |
| **C** | アクセシビリティ / ビジュアル一貫性 / i18n |

---

## エグゼクティブサマリ

VRCT の設定画面は、**部品の作りは良いが、全体の設計が欠けている**という一言に集約されます。

デザイントークンは `variables.css` に一元化されハードコード色は実質 1 件、`Templates.jsx` による設定行の抽象化も効いており、`_useBackendErrorHandling.js` は約 40 種のエラーコードを個別文言に落とし込んでいます。この規模の個人開発デスクトップアプリとしては相当に規律のあるコードベースです。

一方で、3 名が独立に到達した結論は共通していました。

1. **「初めて使う人を使える状態まで運ぶ」仕組みが存在しない** — ウィザードもチェックリストも検索もなく、10 個の設定タブが完全に等価な見た目で並ぶだけ。
2. **設定同士の依存関係が UI 上で切れている** — とくに「API キーを登録する場所」と「翻訳エンジンを選ぶ場所」が別画面で、相互リンクが 1 本もない。
3. **キーボード操作が事実上不能** — フォーカスリング 0 件、`aria-*` 2 件、見出し要素 0 件、クリック可能な `<div>` 14 件。

さらに、UX レビューの過程で**機能バグが 3 件**見つかりました（後述「検証済みの実装バグ」）。うち 1 件は API キーが常に平文表示されるものです。

---

## 3 名が独立に指摘した共通課題（＝最優先）

観点が違う 3 名が別々に到達した指摘は、それだけ確度が高いものとして扱います。

### 共通 1. 翻訳エンジンの選択と認証キー登録の分断

- A: 課題 2 / B: 課題 2 として独立に指摘。
- Config > Translation タブ（[Translation.jsx:30-64](src-ui/views/app/config_page/setting_section/setting_box/translation/Translation.jsx:30)）には 9 エンジン分の**認証キー欄しかなく**、エンジン自体の選択はメイン画面側にあります。
- この分断を UI ではなく**文章で埋めようとしている**のが `locales/ja.yml:160`（DeepL の desc「メイン画面にある翻訳エンジンを DeepL_API に変更してください」）ですが、他エンジンの同等の desc は**ソース上でコメントアウトされたまま**です（`Translation.jsx:185` Plamo / `247` Gemini / `308` OpenAI / `369` Groq / `430` OpenRouter / `508` LM Studio の計 6 件）。生きている `desc` は 3 箇所しかありません。
- 結果として「Gemini のキーを保存 → 成功トーストが出る → メイン画面に戻っても何も変わらない」という、成功表示を伴う完全な行き止まりが発生します。

### 共通 2. Translation タブが 21 行フラット・セクション見出しゼロ

- A: 課題 1 / B: 課題 13（ローカル LLM の ❌ 表示）/ C: 課題 7（ラベル折り返し）が同じ場所に集中。
- `Translation.jsx` は 684 行あり、`SectionLabelComponent` の使用は **0 件**（裏取り済み）。9 エンジン分の設定が一列に並びます。
- 実際に使うエンジンは通常 1 つですが、残り 8 エンジンの認証キー欄・モデル選択が常時スクロール経路に居座ります。
- 加えて [ConnectionCheckButton.jsx:7-11](src-ui/views/app/config_page/setting_section/setting_box/_components/connection_check_button/ConnectionCheckButton.jsx:7) は 2 値判定（`variable === true` 以外はすべて失敗扱い）のため、**LM Studio / Ollama を使う気のないユーザーにも赤い ❌ が 2 つ表示されます**。

### 共通 3. Transcription タブの Advanced セクション

- A: 課題 6 / B: 課題 15 / C: 課題 12 で三重に指摘。裏取り済み。
- [Transcription.jsx:302-303](src-ui/views/app/config_page/setting_section/setting_box/transcription/Transcription.jsx:302) がセクションラベルを 2 枚連続描画しています。

```jsx
<SectionLabelComponent label="Advanced Settings (Whisper Model)" />   // i18n 未対応
<SectionLabelComponent label={t("config_page.transcription.section_label_transcription_engines")} />  // 202 行目と重複
```

- 1 枚目はハードコード英語かつサイドバーの別タブ名（`advanced_settings`）と衝突。2 枚目は同ファイル 202 行目の見出しと完全重複。配下 4 項目の label/desc もすべて英語直書き（`Mic Avg Logprob` / `Default: -0.8`）。

### 共通 4. キーボード操作・無効状態の扱い

- B: 課題 9 / C: 課題 1・2・4 で重複。
- `pointer-events: none` による擬似的な無効化が **19 件**に対し、実 `disabled` 属性は **2 件**。つまり無効表示のコントロールは**Tab キーでフォーカスすれば操作できてしまいます**。
- とくに [ThresholdEntry.jsx](src-ui/views/app/config_page/setting_section/setting_box/_components/threshold_component/threshold_entry/ThresholdEntry.jsx) は「Auto」表示中でもキーボードで編集して送信可能。

---

## 検証済みの実装バグ

UX レビューの副産物として、コードで確認できた明確なバグです。

### バグ 1【重大】API キーが常に平文表示される

[_Entry.jsx:31](src-ui/views/app/config_page/setting_section/setting_box/_components/_atoms/_entry/_Entry.jsx:31) が `type` ではなく `text` という**存在しない属性**を出力しています。

```jsx
<input
    ref={inputRef}
    text={props.text ? props.text : "text"}   // ← type のタイポ
```

`text` prop はリポジトリ内のどこからも渡されておらず、全 Entry が `type` 未指定（＝ text 扱い）になります。結果、[AuthKey.jsx:41](src-ui/views/app/config_page/setting_section/setting_box/_components/auth_key/AuthKey.jsx:41) 経由の DeepL / Gemini / OpenAI / Groq / OpenRouter の API キーが常に画面に平文で出ます。修正は 1 行（`type={props.type || "text"}`）＋ `AuthKey` に `type="password"` を渡すだけです。

### バグ 2【重大】未分類エラーで設定項目が再起動まで操作不能になる

設定変更は必ず `pending()` を経由しますが、pending を解除するのは成功レスポンスか `_useBackendErrorHandling.js` の各 case のみです。ところが未分類パスは通知を出すだけで store を触りません（裏取り済み）。

- [useReceiveRoutes.js:196-199](src-ui/logics/useReceiveRoutes.js:196) — `case 500:` は `showNotification_Error` のみ
- [_useBackendErrorHandling.js:363-373](src-ui/logics/_useBackendErrorHandling.js:363) — `GENERAL_EXCEPTION` / `GENERAL_UNKNOWN` / `default` も通知のみ

pending 中はドロップダウンが「Loading...」固定、ラジオとテキスト欄は無効化されるため、**予期しないエラーが 1 回起きるとその項目は VRCT 再起動まで直りません**。`store.js:80` に `errorAtom` が用意済みですが、設定フローからは一度も呼ばれていません。さらにこの 2 つのエラー文言は英語ハードコードです。

### バグ 3【中】選択中のデバイスがリストにないと設定タブが落ちる

[ComputeDevice.jsx:119-121](src-ui/views/app/config_page/setting_section/setting_box/_components/compute_device/ComputeDevice.jsx:119)：

```js
const target_index = findKeyByDeviceValue(currentDeviceList.data, currentSelectedDevice.data);
const computeTypesArray = currentDeviceList.data[target_index].compute_types;
```

`findKeyByDeviceValue` は不一致時に `null` を返すため（同ファイル 44 行目）、`data[null]` → `undefined.compute_types` で TypeError。GPU の抜き差しやドライバ更新で保存済みデバイスが消えると、タブを開いた瞬間に `AppErrorBoundary` へ落ちます。

---

## レビュアー A — 情報アーキテクチャ / ナビゲーション

### 総評

左サイドバー 12 タブ + 右 1 ペインという「タブ → 設定行」の実質 2 階層フラット構造。セクション見出しを使っているのは Transcription / Others / Advanced / VR / Updater のみで、最大ボリュームの Translation は見出しゼロ。検索・ディープリンク・タブ位置の永続化はいずれも無く、「あの設定どこ?」への救済手段がサイドバーの目視スキャンしかありません。Topbar のページタイトル表示は[コメントアウトで無効化](src-ui/views/app/config_page/topbar/Topbar.jsx:32)されており、現在地の手がかりはサイドバーのハイライトのみです。

### 良い点

- タブ ID → コンポーネントの対応が [SettingBox.jsx](src-ui/views/app/config_page/setting_section/setting_box/SettingBox.jsx:20) と [SidebarSection.jsx](src-ui/views/app/config_page/sidebar_section/SidebarSection.jsx:45) の 2 箇所に集約され、**タブ再編のコストが構造的に低い**。
- 常用タブ群と非設定コンテンツ（Supporters / About）がサイドバー上で視覚的に分離されている。
- `LabelComponent` の `add_warnings` により「なぜ今この設定が使えないか」をその場に出す仕組みが既にある（[Others.jsx:116-121](src-ui/views/app/config_page/setting_section/setting_box/others/Others.jsx:116)、[AdvancedSettings.jsx:118-123](src-ui/views/app/config_page/setting_section/setting_box/advanced_settings/AdvancedSettings.jsx:118)）。

### 主な課題

| 重要度 | 課題 | 要点 |
|---|---|---|
| 高 | Translation タブが 21 行フラット | 共通課題 2 を参照 |
| 高 | エンジン選択とキー登録の分断 | 共通課題 1 を参照 |
| 高 | **設定検索が存在しない** | 12 タブ・約 100 項目に総当たりスキャンしか手段がない。「フォントサイズ」だけで Appearance / VR / Advanced の 4 箇所に候補が散る |
| 高 | **Advanced Settings の 6 割が OBS 配信用の見た目設定** | 16 項目中 10 項目が OBS Browser Source のフォント・色・表示時間（[AdvancedSettings.jsx:274-487](src-ui/views/app/config_page/setting_section/setting_box/advanced_settings/AdvancedSettings.jsx:274)）。同じ意味論の設定が VR タブ / Appearance タブ / Advanced タブと出力先ごとに 3 分散 |
| 高 | **Others が「分類できなかったもの」の吸収先** | 「VRChat へ送信」「翻訳済みのみ送信」というアプリ中核の挙動が「その他」に入っている。6 グループ中 3 つが見出しなし |
| 中 | 段階的開示がほぼ皆無 | 折りたたみは VR タブの 2 値切替のみ。Whisper の Avg Logprob が基本設定と同じ重みで並ぶ |
| 中 | 条件付き表示の欠如 | Google 選択時も Whisper 専用パラメータが全部表示されたまま（[Transcription.jsx:210-226](src-ui/views/app/config_page/setting_section/setting_box/transcription/Transcription.jsx:210)） |
| 中 | タブ切替でスクロール位置が必ず 0 に戻る | [SettingSection.jsx:17-19](src-ui/views/app/config_page/setting_section/SettingSection.jsx:17)。保存/復元フックは実装済みだがタブ単位では未使用 |
| 中 | サイドバー折りたたみ時にツールチップなし | アイコンのみ 12 個。さらに hover 展開が `flex` レイアウトを押し縮め、**本文全体が 8rem 横にずれる** |
| 低 | `side_menu_labels` に 3 タブ分のキーが欠落 | VR / Supporters / About VRCT が [SidebarSection.jsx:103-108](src-ui/views/app/config_page/sidebar_section/SidebarSection.jsx:103) でハードコード。`SectionTitleBox` を復活させると生キーが表示される |
| 低 | 用語の不統一 | `Speaker2Chatbox`（[Others.jsx:44](src-ui/views/app/config_page/setting_section/setting_box/others/Others.jsx:44)）と `Speaker2Log` が同一機能の別名。JA は「DeepL APIキー」だけ「認証キー」表記から外れる |
| 低 | 孤児ロケールキー | `mic_vad_filter` / `speaker_vad_filter` が `locales/en.yml:229,241` などに残るが、**フロント・バックエンド双方に実装なし**（追加調査で確認）。desc にトラブルシュート手順が書かれているため削除が妥当 |
| 低 | VR の「デフォルトに戻す」が巻き添えリセット | [Vr.jsx:46-49](src-ui/views/app/config_page/setting_section/setting_box/vr/Vr.jsx:46) が単一行/複数行の**両プリセット**を確認なしで初期化 |

---

## レビュアー B — オンボーディング / タスク完遂 / フィードバック

### 総評

エラーコードの分類粒度は同種ツールの中でも際立って丁寧です。一方で「初めて入れた人が翻訳を使えるようになるまで」を助ける仕組みが**設定画面に一つもありません**。加えて保存モデルが 3 系統に分裂しているのに、成功トーストは全項目で同一文言です。

### 良い点

- エラーメッセージが具体的で、UI 状態をサーバ値に巻き戻す（[_useBackendErrorHandling.js:155-178](src-ui/logics/_useBackendErrorHandling.js:155)）。
- 入力感度の調整がリアルタイム可視化されている。音量チェック + 実測メーター + しきい値スライダーが一体で、[SliderAndMeter.jsx:84](src-ui/views/app/config_page/setting_section/setting_box/_components/threshold_component/slider_and_meter/SliderAndMeter.jsx:84) がしきい値の上下でメーター色を切り替える。**この画面で最も優れた設計**。
- 依存関係のロックに理由が表示される箇所がある（[AdvancedSettings.jsx:116-134](src-ui/views/app/config_page/setting_section/setting_box/advanced_settings/AdvancedSettings.jsx:116)）。他の課題の多くは「このお手本を横展開していない」ことに尽きます。

### 主な課題

| 重要度 | 課題 | 要点 |
|---|---|---|
| 高 | **オンボーディングが存在しない** | `onboard|wizard|tutorial|first_launch` の全文検索が `src-ui` で 0 件。必要な 4 ステップ（マイク選択→感度→言語→エンジン）が device タブとメイン画面に散っており、設定画面はそれを一切案内しない |
| 高 | エンジン選択とキー登録の分断 | 共通課題 1 を参照 |
| 高 | **保存モデルが 3 系統に分裂し、トーストが全項目同一** | 即時自動保存（ドロップダウン/スイッチ/ラジオ）、明示保存ボタン（Entry/AuthKey/Color）、200ms デバウンス保存（スライダー）が混在。成功時はすべて「設定を保存しました。」を 1 秒表示するだけで、**どれが保存されたか特定できない** |
| 高 | pending 固着 | バグ 2 を参照 |
| 高 | **アップデート実行に確認がない** | [Updater.jsx:182-192](src-ui/views/app/config_page/setting_section/setting_box/updater/Updater.jsx:182) の「この設定でインストール」が確認ダイアログなしで即実行。押した瞬間に画面全体が更新中表示に差し替わり戻れない。**ダウングレードと CPU/GPU 切替（数 GB）が 1 クリックで走る** |
| 高 | **モデル DL を中断できない** | [_DownloadButton.jsx:11-23](src-ui/views/app/config_page/setting_section/setting_box/_components/_atoms/_download_button/_DownloadButton.jsx:11) にキャンセル UI なし。`large-v3` は 2.87GB、`nllb-200-3.3B` は 3.3GB。強制終了以外の脱出手段がない |
| 中 | **モデル名が生の内部 ID のまま** | `nllb-200-distilled-1.3B-ct2-int8 (1.3GB)` がそのまま並ぶ。`locales/ja.yml:249-250` に `recommended_model_template: "{{model_name}} モデル （{{capacity}}） [推奨]"` が**用意済みなのに未使用**。初回ユーザーに最も価値のある `[推奨]` 表示が失われている |
| 中 | Enter キーで保存できない | `_Entry.jsx:38` に `onKeyDown` の受け口があるのに、渡しているのは `HotkeysEntry` だけ。API キー貼り付け後の Enter、ワードフィルタ入力後の Enter が無反応 |
| 中 | キーボード操作不能 | 共通課題 4 を参照 |
| 中 | しきい値欄にバリデーションがない | 空にすると確認なく即座に `"0"` を送信（[ThresholdEntry.jsx:19-21](src-ui/views/app/config_page/setting_section/setting_box/_components/threshold_component/threshold_entry/ThresholdEntry.jsx:19)）。0 は常時マイク反応。`type="number"` も `min`/`max` もなし |
| 中 | Undo もリセットもほぼ無い | 「デフォルトに戻す」は VR タブの 1 つだけ（しかも確認なしの一括破壊）。Whisper の Avg Logprob は desc に "Default: -0.8" と書いてあるのに、戻す手段がなく手で合わせ直すしかない |
| 中 | 処理タイプの用語が難解 | `int8_bfloat16` / `int8_float16` の中間項目は[生の ID がそのまま表示](src-ui/views/app/config_page/setting_section/setting_box/_components/compute_device/ComputeDevice.jsx:100)。補足がつくのは先頭と末尾の 2 つだけ |
| 中 | 使わないローカル LLM に ❌ が出る | 共通課題 2 を参照 |
| 中 | **モデル未 DL でも Whisper を選択できる** | モデル選択側は `disabled: !item.is_downloaded` で正しく無効化しているのに、エンジン選択側（[Transcription.jsx:210-226](src-ui/views/app/config_page/setting_section/setting_box/transcription/Transcription.jsx:210)）には条件も desc もない。切替は成功トーストを出すため、動かないことにメイン画面で初めて気づく |
| 低 | OSC / WebSocket に説明が皆無 | `locales/ja.yml:381-392` は label のみで desc なし。OSC IP の設定ミスは他機能を自動無効化する副作用がある |
| 低 | ドキュメントリンクが常に英語 | [AboutVrct.jsx:158](src-ui/views/app/config_page/setting_section/setting_box/about_vrct/AboutVrct.jsx:158) が `generateLocalizedDocumentUrl()` を引数なしで呼んでいる。メイン画面側（`RightSideComponents.jsx:33`）は正しく言語を渡しており不整合。**検証時に `SplashComponent.jsx:61` にも同じ引数漏れを発見**（config_page 外）。いずれも 1 行修正 |

### 初回ユーザーのつまずきシナリオ

**シナリオ A — 「API キーを入れたのに翻訳が英語のまま」**
デバイスタブでマイクを選び、音量メーターが動いたので安心。翻訳タブで Gemini のキーを取得・保存し、緑の成功トーストを確認。グレーアウトしていたモデル選択も選べるようになり、これも保存成功。メイン画面に戻って喋るが、翻訳は一切変わらない。翻訳タブを 3 回見直すが、DeepL の項目にだけある「メイン画面で翻訳エンジンを変更してください」という一文は自分に関係ないと判断して読み飛ばす。最終的に「Gemini は対応していないのかも」と結論。**実際にはメイン画面でエンジンを切り替えるだけで動く状態だった。**

**シナリオ B — 「感度を触っていたら設定欄が固まった」**
手動モードにして数値欄の `300` を BackSpace で全消し。空になった瞬間に `"0"` が送信される（気づかない）。`800` と打つ間に `8` → `80` → `800` と 3 回送信され、メーターが激しく動くのを見て「壊した?」と不安になる。戻そうにもデバイスタブにリセットボタンはなく、元の値も覚えていない。この試行中にバックエンドが未分類の例外を返すと、英語のエラーが出たまま項目が pending に固着し、以後入力不能に。「バグってる」と判断して VRCT を閉じる。

**シナリオ C — 「アップデートしたら古いバージョンに戻された」**
アップデートタブで「デバイス構成」の意味が分からないまま、GPU があるので GPU 版を選択（3.5GB の追加 DL が必要とはこのタブに書かれていない）。バージョンのドロップダウンは一番下が最新だと思い込んで一番下を選ぶ（実際は[先頭に「- 最新」が付き下ほど古い](src-ui/views/app/config_page/setting_section/setting_box/updater/Updater.jsx:83)が、開いた状態では先頭が見えていなかった）。**確認ダイアログなしで実行**され、画面全体が更新中表示に。数 GB の DL の末に起動したのは GPU 版の半年前のバージョン。直そうとして、また数 GB をダウンロードすることになる。

---

## レビュアー C — アクセシビリティ / 一貫性 / i18n

### 総評

デザイントークンの規律は高水準。一方でキーボード操作とセマンティクスは事実上未対応で、config_page 全体で見出し要素 0 件、ランドマーク 0 件、`:focus` スタイル 0 件、`aria-*` 0 件。加えて `reset.css` が全フォームコントロールに `outline: none` を当てているため、正しく `<button>` を使っている箇所ですらフォーカス位置が見えません。

> **注**: レビュー依頼時に「`_components` と `_atoms` の二重実装」を懸念点として提示しましたが、これは**誤りでした**。`SwitchBox.jsx` は 12 行、`Entry.jsx` は 9 行の薄いラッパで、ロジックの重複はありません（裏取り済み）。実際の重複は別の場所にあります（課題 4 の `.save_button`）。

### 定量データ（実測）

**セマンティクス / キーボード**

| 指標 | 値 |
|---|---|
| `aria-*` の使用（全 `src-ui`） | **2 件** |
| `role=` の使用（全 `src-ui`） | **1 件** |
| `tabIndex` | config_page **0 件** |
| `<h1>`〜`<h6>` | 全 `src-ui` **0 件** |
| `<nav>/<main>/<section>/<ul>/<li>` | config_page **0 件** |
| `:focus` / `:focus-visible` スタイル | **1 件**（`SliderAndMeter.module.scss:52`、中身は `outline: none`）。`src-ui` 全体でもこの 1 件のみ |
| `onClick` を持つ `<div>` | **14 件**（`<button>` は 18 件 / `onClick` 総数 40） |
| 名前のないアイコンのみボタン | **6 件** + 共通 3 コンポーネント |
| `<img>` / うち `alt` 付き | **42 件 / 7 件** |
| `<label htmlFor>` の適切な使用 | **0 件** |
| `pointer-events: none` による擬似無効化 | **19 件** |
| 実 `disabled` 属性 | **2 件** |

**一貫性 / 色**

| 指標 | 値 |
|---|---|
| ハードコード 16 進カラー（SCSS） | **1 件**（`MessageFormat.module.scss:73`） |
| インライン `style` の色指定 | **4 件**（`Plugins.jsx:109-112` の `color:"red"`） |
| AA (4.5:1) 未達が疑われるテキスト | **8 組** |
| 1.4.11 (3:1) 未達の UI 輪郭 | **5 組** |
| `border-radius` の値の種類 | **15 種**（`0.4rem` が 26 件で支配的） |
| 完全同一の `.save_button` ブロック複製 | **3 ファイル** |
| 「主要ボタン」の視覚スペック | **5 種類** |
| 実質未使用トークン | `--config_page_sidebar_width`（16.8rem 定義／サイドバー実装は 12rem ハードコード）。参照は `topbar/title_box/TitleBox.module.scss:3` の 1 箇所だけだが、`TitleBox` 自体が `Topbar.jsx:32` でコメントアウトされており描画されない |

**国際化**

| 言語 | キー数 | en 比欠落 | 空値（null） |
|---|---|---|---|
| en | 281 | — | 0 |
| ja | 281 | 0 | 0 |
| ko | 277 | 4 | **55** |
| zh-Hans | 277 | 4 | **42** |
| zh-Hant | 277 | 4 | **42** |

`i18next` は `returnNull: false` が既定のため、空値は英語にフォールバックします（＝空欄バグではなく**英語混在**）。空値が集中しているのは `updater.install_panel`（11 キー、3 言語すべて）、`translation.*`（19 キー、3 言語すべて）、`common.connection_check`。**`updater.install_panel` は本ブランチで追加された新 UI であり、リリース前に片付ける価値があります。**

`t()` 未経由の英語文字列は **18 件**（うち固有名詞として許容できるのは 4 件程度）。

### 主な課題

| 重要度 | 課題 | 要点 |
|---|---|---|
| 高 | **フォーカスリングが全画面に一つもない** | `reset.css:245` が全フォームコントロールに `outline: none`。`src-ui` 全体で `:focus` 定義は 1 件のみで、その中身も `outline: none`（`SliderAndMeter.module.scss:52`）。WCAG 2.4.7 の明確な違反 |
| 高 | 主要コントロールが `<div onClick>` | サイドバータブ、トグル、ドロップダウン、VR のセグメント切替。さらに `SidebarSection.module.scss:66` が選択中タブに `pointer-events: none` を当て、**現在のタブはヒットテストからも消えている** |
| 高 | チェックボックスのアクセシブルネームが全件空 | `Checkbox.jsx` の `checkboxId` が**どこからも渡されていない**。可視ラベルは `Templates.jsx` の兄弟要素にあり、`<label>` の中身は SVG のみ |
| 高 | 無効状態が CSS だけ | 共通課題 4 を参照 |
| 高 | **CTA と無効状態のコントラストが AA 未達** | インストールボタン **3.84:1**、Update ボタン **2.67:1**、無効時 **2.39:1**、無効ボタン面 vs 背景 **1.34:1**（押せるか否かがほぼ判別できない）。`Plugins.jsx` の `color:"red"` は **3.59:1**。※ トークン値からの計算値であり、実機での再確認を推奨 |
| 中 | ページ全体が選択不可 + 見出しゼロ | `root.css:9-10` の `* { user-select: none; }` により、**認証キー・URL・バージョン・エラーメッセージがコピーできない**。`VersionLabel` にコピーボタンがあるのは、この制約の回避策が必要になった証拠 |
| 中 | 長い訳文でラベルとコントロールが衝突 | `LabelComponent.module.scss` の `white-space: nowrap` + `width: max-content` が親の折り返し指定に勝つ。`text-overflow` もないため**そのまま重なる**。最長ラベルは en の 48 文字（`Transcription Engine Used For Speech Recognition`）で、**既定言語で崩れる** |
| 中 | `.save_button` が 3 ファイルに完全複製 | AuthKey / EntryWithSaveButton / ColorEntryWithSaveButton が一字一句同じ。主要ボタンの見た目も 5 通りに分裂（`ConnectionCheckButton` は静止時に背景も枠線もなく、ただのテキストに見える） |
| 中 | ドロップダウンが親にクリップされる | `SettingSection.module.scss` の `overflow-y: scroll` がクリッピング文脈になり、ページ下部でメニューが切れる。選択中のハイライトもなく、閉じる操作が `onMouseLeave` 依存で Escape も外側クリックもない |
| 中 | レイアウト値と実寸の乖離 | `--config_page_topbar_height: 8rem` を確保しているのに Topbar の実体は `height: 1rem` で、**約 70px の空白帯が常に存在**（コメントアウトされた `TitleBox` の名残）。`ui_scaling` は 40〜200% でルートフォントが **4px〜20px** になる一方、`tauri.conf.json` の `minWidth: 400` は物理 px 固定 |
| 中 | ko / zh の空値 | 上記の表を参照 |
| 低 | `t()` 未経由 18 件 / アイコンボタンに名前がない 6 件 / `<img alt>` 42 件中 7 件 | — |

---

## 統合ロードマップ

3 名の提案を統合し、**費用対効果順**に並べたものです。

### フェーズ 0 — 即日〜1 日（バグ修正、リスク極小）

| # | 内容 | 対象 | 工数 |
|---|---|---|---|
| 0-1 | `_Entry.jsx:31` の `text=` → `type=` 修正 + `AuthKey` に `type="password"` | バグ 1 | 15 分 |
| 0-2 | 500 / `GENERAL_*` / `default` パスで `error<Base>()` を呼び pending を解除。英語ハードコードのエラー文言を `locales` へ | バグ 2 | 0.5〜1 日 |
| 0-3 | `ComputeDevice.jsx:119` に null フォールバック（先頭デバイスへ復帰 + 通知） | バグ 3 | 1 時間 |
| 0-4 | `Transcription.jsx:302-303` の重複セクションラベル削除 + 8 件の英語 label/desc を i18n 化 | 共通課題 3 | 2 時間 |
| 0-5 | `AboutVrct.jsx:158` に `currentUiLanguage.data` を渡す | B 課題 17 | 1 行 |
| 0-6 | 孤児ロケールキー `mic_vad_filter` / `speaker_vad_filter` の削除 | A 課題 13 | 15 分 |

### フェーズ 1 — 1〜2 週間（体験への効果が最大）

| # | 内容 | 効く課題 | 工数 |
|---|---|---|---|
| 1-1 | **アップデート実行前の差分確認ダイアログ**（現在→変更後、CPU/GPU、DL 容量、ダウングレード警告）。表示に必要な値は `Updater.jsx` 内で算出済み | シナリオ C、B 課題 5 | 1〜2 日 |
| 1-2 | **モデル選択ラベルの人間向け化** — 既に 5 言語すべてに存在する `recommended_model_template` を使い `[推奨]` を復活。ID は小さい副次表示へ降格。**追加の翻訳作業ゼロで効果が最大** | B 課題 7 | 0.5 日 |
| 1-3 | **フォーカスリング復活 + `_atoms` 3 コンポーネントのセマンティック化**。`:focus-visible` トークン追加（30 分）＋ `_SwitchBox` / `_DropdownMenu` / `_Entry` を `<button>` / `disabled` ベースへ。この 3 ファイルがドロップダウン 22・全トグル・全テキスト入力の実体で、**最小の変更で最大面積をカバーする唯一のポイント**。第一段は「Tab で到達 / Enter で開閉 / Escape で閉じる」まで | C 課題 1・2・4、B 課題 9 | 2〜3 日 |
| 1-4 | **コントラスト是正** — `--on_primary_color` / `--disabled_bg_color` / `--control_border_color` を追加し 13 箇所を置換。`Updater.module.scss` の `opacity: .6` 削除だけで無効ボタンが 2.39:1 → 3.7:1 に | C 課題 5 | 0.5〜1 日 |
| 1-5 | **Translation タブをエンジン単位のセクション化**（`SectionLabelComponent` 導入なら 1〜2 時間、選択中エンジンのみ展開するアコーディオンまで含めて 1 日）。あわせて `ConnectionCheckButton` を 3 値化（未確認 / 接続済み / 失敗） | 共通課題 2、A 課題 1・8、B 課題 13 | 1 日 |
| 1-6 | **保存フィードバックの具体化 + Enter キー対応** — トーストに項目名を差し込む。`_Entry.jsx:38` の既存受け口に `onKeyDown` を渡す（各 1 行） | B 課題 3・8 | 1〜2 日 |
| 1-7 | **ko / zh の空値解消 + CI ガード** — `updater.install_panel`（11）→ `translation.*`（19）→ `connection_check`（4）の順。整合性チェックは 20〜30 行 | C 課題 11 | スクリプト 0.5 日 + 翻訳 |

### フェーズ 2 — 1〜2 ヶ月（構造の作り直し）

| # | 内容 | 効く課題 | 工数 |
|---|---|---|---|
| 2-1 | **「はじめに」タブ（セットアップチェックリスト）** — マイク選択 / 感度確認 / 言語設定 / エンジン選択の 4 項目を完了状態つきで表示し、各項目から該当タブへジャンプ。判定は既存フックの状態を読むだけで、新規ロジックは最小限。**シナリオ A・B・C すべての根本原因に効く** | B 課題 1、共通課題 1 | 3〜5 日 |
| 2-2 | **タブ再編** — OBS Browser Source を独立タブ化（あるいは「出力先」タブに VR / OBS / Chatbox を集約）、Others の送信系を「Messaging」として分離。コンポーネントは既に細粒度なので JSX の並べ替え + ロケールキー移設が中心 | A 課題 4・5 | 1 日 |
| 2-3 | **ラベルとコントロールの関連付け** — `Templates.jsx` に `useId()` を導入し `aria-labelledby` を配る。1 ファイル + `LabelComponent` の改修で**チェックボックス 14・ドロップダウン 22・スライダー 19・ラジオ 6 の計 60 以上が一括で名前を得る** | C 課題 3 | 1.5〜2 日 |
| 2-4 | **レイアウト破綻の解消** — (a) `LabelComponent` の `white-space: nowrap` 除去 + `flex-wrap: wrap`、(b) サイドバーをオーバーレイ展開にして hover 時の全体シフトを止める、(c) ドロップダウンの `createPortal` 化 + 選択中ハイライト | C 課題 7・9・10、A 課題 10 | 1.5〜2 日 |
| 2-5 | **設定検索** — サイドバー上部に検索欄を置き、ロケールの label/desc を横断インデックス化。ラベルが `t()` キーで統一済みのためインデックス生成は自動化できるが、項目アンカー付与が全タブに波及。**以降タブ分類を多少誤っても致命傷にならなくなる** | A 課題 3 | 2〜3 日 |
| 2-6 | **ボタンの共通化 + 段階的開示** — `_atoms/_Button.jsx`（`variant` × `size` の 2 軸）で 5 種の主ボタンと 3 複製を集約。あわせて各タブに「詳細設定を表示」トグルを導入 | C 課題 8、A 課題 7 | 2 日 |
| 2-7 | **タブ別スクロール位置の記憶 + リセット手段の整備** — 保存/復元フックは実装済みでタブ ID のキー分けを足すだけ。各項目に「既定値と異なるときだけ現れるリセットアイコン」、VR の一括リセットには確認ダイアログ | A 課題 9・14、B 課題 11 | 1 日 |
| 2-8 | **モデル DL のキャンセル + 事前の容量確認** — 容量データは `ui_configs.js` に既にある | B 課題 6 | 1〜2 日 |

---

## 設計判断が必要な未解決事項

コードの修正だけでは決められない、方針を決める必要がある項目です。

1. **`Speaker2Chatbox` / `Speaker2Log` の呼称統一** — 同一機能の別名が UI 内に併存。どちらに寄せるかを決めてから、全ロケールと `Others.jsx:44` を一括置換する必要があります。
2. **`ui_scaling` の下限 40%** — ルートフォント 4px、最小文字 3.2px を生みます。実用下限として 70〜80% への引き上げが妥当かどうか。あわせて `tauri.conf.json` の `minWidth: 400`（物理 px 固定）を `setMinSize()` で `ui_scaling` に連動させるか。ただし既存ユーザーのウィンドウジオメトリ保存（`useWindow.js` の `asyncSaveWindowGeometry`）と干渉しうるため、**実機検証を挟むこと**。
3. **`--config_page_topbar_height: 8rem` の空白帯** — コメントアウトされた `TitleBox` / `SectionTitleBox` を復活させて埋めるか、変数を実寸（2rem 程度）に合わせるか。復活させる場合は `side_menu_labels` の欠落 3 キー（VR / Supporters / About VRCT）を先に埋めないと生キーが表示されます。
4. **UI 言語設定の置き場所** — 現在は Appearance タブ（JA では「デザイン」）の先頭。「デザイン」から UI 言語を探すのは困難で、独立させるか JA を「表示・言語」に改称するか。
5. **`user-select: none` の緩和範囲** — 全面解除ではなく、`p` / `input` / 説明文 / エラーメッセージに限定して `user-select: text` を戻す方針で良いか。
