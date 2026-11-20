# AMD 版の UI 引き継ぎ

AMD 版に必要な UI の動作（更新先の選択・送信、版表示、VR からの更新拒否、翻訳キー）は実装済み。見た目の調整と、Radeon 実機での確認が残っている。

## 1. 起動時に届く値

`/run/initialization_complete` に含まれる 2 つの値を使う。

| キー | 値 | UI の受け取り |
|---|---|---|
| `/get/data/compute_mode` | この起動で使える計算モード `"cpu" \| "cuda" \| "amd"` | `useComputeMode().currentComputeMode` |
| `/get/data/installed_edition` | インストール済みの版 `"cpu" \| "cuda" \| "amd"`（読み取りのみ） | `useComputeMode().currentInstalledEdition` |

`installed_edition` は同梱の DLL（`_internal/ct2-rocm/ctranslate2.dll`、`_internal/cublas64_12.dll`）から判定するので、GPU やドライバーの状態に左右されない（`native/vrct-backend/src/compute.rs` の `installed_edition`）。AMD 版や CUDA 版が GPU を使えず CPU で動くときは、`COMPUTE_MODE` が `"cpu"`、`installed_edition` が版のままになる。

AMD の対象は RDNA3（RX 7000）、RDNA3.5（gfx1150・1151）、RDNA4（RX 9000）。最近の AMD Adrenalin ドライバーに含まれる HIP ランタイム `amdhip64_7.dll` を使う。ドライバーが古い場合や対象外の Radeon では、AMD 版を入れたまま CPU で動く。

## 2. 実装済みの内容

| 箇所 | 内容 |
|---|---|
| `src-ui/logics/common/useUpdateSoftware.js` | 版ごとの endpoint を `UPDATE_SOFTWARE_ENDPOINTS`（cpu / cuda / amd）にまとめ、`updateSoftware(edition, version)` で送る。表にない版は送らない |
| `src-ui/logics/useReceiveRoutes.js` | `/get/data/installed_edition` と `/run/update_amd_software` を登録 |
| `src-ui/logics/common/vrPanelWire.js` | VR パネルから CPU・CUDA・AMD のどの更新も開始できない（テスト済み） |
| `config_page/setting_section/setting_box/updater/Updater.jsx` | 更新先の初期値と「現在」の列を `installed_edition` から決める。選択肢に AMD を追加。版が分からない間は実行ボタンを無効にする。AMD を選ぶと容量の注意を出す |
| `config_page/version_label/VersionLabel.jsx` | 実行モードが AMD のときは「AMD」の印（通常・コンパクト・β、コピー文字列）。CPU で動作中は印なし |
| `others/error_boundary/AppErrorBoundary.jsx` | 「Update Now」は導入済みの版で最新版を要求。版が分からない間は無効 |
| `locales/*.yml` | `update_modal.compute_mode_amd`、`update_modal.warn_amd_extra_size` を追加し、`compute_mode_desc` に AMD を追記 |

更新の送受信は 3 つとも同じ形。最新版なら `data` は省略または `null`、版を固定するならリリース一覧の `version` 文字列を渡す。失敗時は同じ endpoint に `UPDATE_SOFTWARE_DOWNLOAD` または `UPDATE_SOFTWARE_VERIFY` が届き、既存の共通処理が表示する。

| 更新先 | endpoint | セットアップの引数 | 取得する ZIP |
|---|---|---|---|
| CPU | `/run/update_software` | `/EDITION=cpu` | `VRCT.zip` |
| NVIDIA | `/run/update_cuda_software` | `/EDITION=gpu` | `VRCT_cuda.zip` |
| AMD | `/run/update_amd_software` | `/EDITION=amd` | `VRCT_amd.zip` |

## 3. 設計者に任せる点

- 選択肢が 3 つになったアップデーターと、版表示の「AMD」の印の見た目。
- フォールバック中に導入済みの版も示すか（例「AMD 版（CPU で動作中）」）。今は実行モードの印だけを出す。
- AMD の初回配布より前のリリースには AMD 用 ZIP がない。その版を AMD で選ぶと取得失敗のエラーになる。選択肢で防ぐかどうか。

## 4. 翻訳・文字起こしのデバイス選択

`/get/data/selectable_translation_compute_device_list` と `/get/data/selectable_transcription_compute_device_list` の GPU 要素には `vendor`（`"amd"` または `"nvidia"`、CPU では省略）が付く。CT2 に渡す `device` は Radeon でも `"cuda"`。今の UI は `device_name` をそのまま出すので変更なしで動く。

```json
{"device":"cuda","device_index":0,"device_name":"AMD Radeon RX 7800 XT","compute_types":["auto","float16","float32"],"vendor":"amd"}
```

## 5. 配布前の確認

- 対応 Radeon で、版表示・コピー・確認画面が AMD を示し、設定からの版指定とエラー画面からの最新版更新のどちらも AMD の endpoint に届くこと。
- 同じ AMD 版を CPU で動かし、更新先の初期値が AMD のままであること。CPU / NVIDIA から AMD を明示的に選ぶ場合も確認する。
- 通信失敗・検証失敗で既存のエラー表示と更新操作の復帰が働くこと。
