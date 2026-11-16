# VR UI のログ窓の字幕の形 — デスクトップ設定画面の担当への引き継ぎ (P2.5 段階 1)

VR UI のログ窓 (panel) に「表示の形」を足した。履歴 (今までのログ窓) / 字幕・複数行 / 字幕・1行 を、
VR のログ窓の操作バーの形のボタンで切り替える。2 枚目の窓は作っていない。
デスクトップの設定画面 (`src-ui/views/app/config_page/...`) は触っていない。

## 変わっていないもの

- small / large のオーバーレイ (Rust で画像を描くもの)、その endpoint
  (`overlay_small_log*` / `overlay_large_log*`)、設定 (`OVERLAY_SMALL_LOG_SETTINGS` /
  `OVERLAY_LARGE_LOG_SETTINGS`)、契約テストの既存ケース。
- 履歴の形の設定は今までどおり `OVERLAY_VR_PANEL_SETTINGS` と `OVERLAY_VR_PANEL_LOCKED`。

## 設定 (config.json)

| 名前 | 型 | 既定 | 中身 |
|---|---|---|---|
| `OVERLAY_VR_PANEL_FORM` | str | `"history"` | `history` / `multi_line` / `single_line` のどれか |
| `OVERLAY_VR_SUBTITLE_SETTINGS` | dict | 下 | `{"multi_line": {...}, "single_line": {...}}` |

字幕の形ごとのキー: `width` `height` (ログ窓の論理 px) `x_pos` `y_pos` `z_pos` `x_rotation`
`y_rotation` `z_rotation` `display_duration` (秒、int) `fadeout_duration` (秒、int、0 で消えない)
`opacity` (0.2–1.0) `ui_scaling` (板の幅 m) `tracker` (`Playspace` / `LeftHand` / `RightHand` / `HMD`)
`locked` (bool、既定 true)。既定は multi_line が 900×700・0.25 m・LeftHand、single_line が
1200×180・1.0 m・HMD (small / large の既定の見た目の大きさに合わせたもの。1 行の板の高さは約 0.15 m)。

範囲 (外れた値は、型違いの値と同じく受け付けずに元の値を保つ。応答は 200):
`opacity` 0.2–1.0、`display_duration` / `fadeout_duration` 0 以上、`ui_scaling` 0.05–3.0、
`width` 600–1400、`height` 120–1000 (字幕の最小の高さは 120px。履歴は今までどおり 400px)。

## endpoint (新しい 5 つ)

| endpoint | data | 返り値 |
|---|---|---|
| `/get/data/overlay_vr_panel_form` | なし | 今の形 |
| `/set/data/overlay_vr_panel_form` | 形の名前 | 今の形。知らない名前は 400 `VALIDATION_CONFIG_VALUE_INVALID`。変わったときは下の push 3 つも出る |
| `/get/data/overlay_vr_subtitle_settings` | なし | 字幕の設定の全体 |
| `/set/data/overlay_vr_subtitle_settings` | 一部の形・一部のキーだけの dict (例 `{"single_line": {"display_duration": 8}}`) | 全体。知らない形・キーは 400 (値の型が違うキーはそのキーだけ元の値を保つ) |
| `/run/vr_panel_log_rendered` | なし | `true`。VR 画面がログ窓の新しい中身を描き終えた合図 (VR 画面だけが送る) |

`set overlay_vr_subtitle_settings` は、今の形が字幕なら表示秒・消える秒・不透明度・ロックをすぐオーバーレイへ
反映する。**位置・大きさ・固定先は、今出ている形には次に形を切り替えるまで反映しない** (段階 2 で必要なら足す)。

## push (新しい 3 つ)

| push | result | いつ |
|---|---|---|
| `/run/overlay_vr_panel_locked` | 今の形のロック | 形を変えたとき、今の形が字幕で `set overlay_vr_subtitle_settings` したとき |
| `/run/overlay_vr_panel_opacity` | 今の形の不透明度 | 同上 |
| `/run/overlay_vr_subtitle_settings` | 字幕の設定の全体 | 字幕の形の値が保存されたとき毎回 (VR で動かした・大きさを変えた (今の形でない形への保存も)、操作バーの不透明度・ロック) |

既存の `/run/overlay_vr_panel_anchor` は、形を変えたときにも出る。

## 意味が変わった既存の endpoint

`/get|set/data/overlay_vr_panel_anchor`、`/get|set/data/overlay_vr_panel_opacity`、
`/get/data/overlay_vr_panel_locked`、`/set/enable|disable/overlay_vr_panel_locked` は
**今の形の値** を読み書きする。形が履歴なら今までと同じ値・同じ返り値。
デスクトップの設定画面にこれらを出す場合、字幕の形の値を変えてしまわないよう、形ごとの値は
`overlay_vr_subtitle_settings` から読み書きするのが安全。

## 挙動 (VR 側)

- 字幕の形は不透明な板 (rgb(41,42,45))。不透明度はオーバーレイ全体に効く。最後の新着から表示秒の後、消える秒で消える。
- ロックした字幕と、消えている字幕はレーザーが当たらない (VRChat の入力を横取りしない)。
  出るのは新着・ログ窓を開いたとき・ランチャーのログボタンの長押しのとき。指しているだけでは出ない
  (見えている間に指していれば消えない)。
- ランチャーのログボタンの長押しで、ロック中の字幕はロックが外れる。HMD に付けた字幕は動かさずに出すだけ、
  それ以外の字幕と履歴は目の前 (部屋に固定) へ呼び戻す。
- 形を変えたとき・字幕を開いたときは、新しい中身が撮れるまで (最大 1.5 秒) 透明。
- VR で動かした位置は、動かしたときの形の枠に保存される。

## 段階 2 以降でやること

- デスクトップの設定画面に、形の選択と形ごとの位置・表示秒・消える秒・不透明度・ロックを出す。
- 字幕の設定の位置・大きさ・固定先の変更を、今出ている形へすぐ反映する (今は形を切り替えたときに反映)。
- small / large のオーバーレイとの役割の整理 (統合・置き換えるかは製品判断)。
- 実機 (VR) での見た目・消え方・ロック中の当たり判定・呼び戻しの確認。
