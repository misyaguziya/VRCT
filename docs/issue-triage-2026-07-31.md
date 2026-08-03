# Open Issues Triage (2026-07-31)

対象: <https://github.com/misyaguziya/VRCT/issues?q=sort%3Aupdated-desc+is%3Aissue+state%3Aopen+>

2026-07-31 時点で open issue は 27 件。GitHub の open pull request 2 件は優先度付け対象から除外した。

## 判定基準

- P0: 起動不能、誤送信、クラッシュ、セキュリティ/信頼性毀損。まず手を付ける。
- P1: コア体験の品質劣化。クラッシュではないが、通話・翻訳・文字起こしの成功率を下げる。
- P2: 重要な改善要望。ユーザー価値は高いが、現時点では回避策があるか対象範囲が限定的。
- P3: 大きい機能追加、調査コストが高い要望、情報不足、重複候補、進行中のもの。

## 実装可否の判定軸

設計書と仕様書から、現行 VRCT の軸は「Windows を主対象にしたリアルタイム文字起こし・翻訳・VR 連携」と読める。よって優先度とは別に、各 issue は以下の観点で実装可否を判断する。

- Fit: コア体験の改善か。文字起こし、翻訳、起動、配信、OSC、オーバーレイの信頼性向上なら強く採用。
- Scope: 現在の対象範囲に収まるか。Windows 主対象から大きく外れるものは、要望が妥当でも即実装しない。
- Cost: 保守コストが継続的に増えるか。新しい推論基盤、OS、GPU スタック追加は高コスト。
- Safety: 誤送信、クラッシュ、情報漏えい、誤検知リスクを下げるか。ここは最優先で採用。
- Evidence: 再現手順、ログ、複数報告があるか。証拠が薄いものは `needs-info` で止める。

## 実装判断ステータス

- Adopt: 設計に合っており、優先度順に実装する。
- Review: 設計適合はあるが、仕様の切り方や回避策を確認してから決める。
- Defer: 要望は妥当だが、今のロードマップでは後ろに置く。
- Reject: 現行設計から外れるか、保守コストに見合わないため積極的には実装しない。
- Close: 重複、PR 対応済み、情報不足解消なしで終了候補。

## 先にやる整理

- Issue #50 と #102 は同系統の `NoneType.close` 系エラーに見える。先に重複か同根かを確認し、同じ原因なら片方に集約する。
- Issue #90 と #98 はどちらも「起動しない」系。再現条件とログ取得方法をテンプレ化して追加情報を取りたい。
- Issue #89 は open PR #95 と対応関係があるため、仕様差分を確認して `blocked-by-pr` 扱いで良い。
- Issue #93 は本文が実質空なので、一定期間で追加情報がなければ close 候補。

## 実装判断の初期案

### Adopt

- #94 AV detection when using Bing
- #50 / #102 `NoneType.close` 系クラッシュ
- #98 / #90 起動不能
- #87 turbo モデルの誤送信系挙動
- #63 Google 音声認識フリーズ
- #76 音声認識失敗率
- #91 Translation engine limit error
- #104 token refresh 導線
- #103 音声認識フィードバック不足

### Review

- #77 I downloaded it, but it's not used.
  理由: 起票内容が曖昧で、インストーラー問題なのか配置仕様の誤解なのか未確定。

- #96 Add a simplified installation program
  理由: プロダクト普及には効くが、配布戦略の判断が必要。

- #100 custom server setting for speech recognition
  理由: コア価値には沿うが、外部 STT の接続面をどこまで開くか設計判断が要る。

- #99 prevent automatically switching to Whisper
  理由: フォールバック設計の一部なので、UX と失敗耐性のバランス確認が必要。

- #54 Limit transcribed message length In/Out
  理由: 効果は高いが、表示側で切るか認識結果側で正規化するかを決める必要がある。

- #27 SE on sending an OSC message
  理由: 情報漏えい抑止の補助策として筋は良いが、まず誤送信そのものを潰す方が先。

### Defer

- #89 Custom API Address
  理由: open PR #95 の結果待ち。

- #81 An error occurred, but it works properly
  理由: 進行中で緊急度が低い。

- #23 Exclude word from translation
  理由: 進行中のため新規優先度付けは不要。

- #97 cohere transcribe
- #78 HY-MT1.5-1.8B
- #75 canary-qwen-2.5b
- #37 SeamlessM4T
- #17 whisper direct translation
  理由: いずれもモデル/プロバイダ追加やパイプライン変更で、既存の品質問題より後ろに置く。

### Reject 候補

- #88 AMD GPU Support VIA RocM
  理由: 現仕様は Windows 主対象で、ROCm は OS/GPU/依存配布の検証面まで一気に広がる。需要がさらに強くならない限り、今は採らない判断が妥当。

- #82 end-to-end multimodal translation with direct audio input
  理由: 現行の STT -> 翻訳パイプラインから大きく外れた別系統アーキテクチャになる。面白いが、現 backlog の延長ではなく別プロダクト級の検討。

- #92 Cannot build on linux
  理由: issue 自体は正当だが、現仕様では Windows 主対象。Linux ビルドを公式に支えるかを先に決めない限り、個別修正で追わない方が良い。

### Close 候補

- #93 本文が空に近い feature request
  理由: 情報不足。

- #89 PR #95 がマージされ、仕様差分が問題なければ close。
- #50 / #102 が同一原因なら片方を duplicate close。
- #90 / #98 が同一原因なら片方を duplicate close。

## 推奨優先順位

### P0

- #94 [Bug]: AV detection when using Bing
  理由: セキュリティソフト検知は実害が大きく、継続利用の信頼を壊す。false positive でも最優先で説明責任が必要。
  推奨対応: 再現条件の切り分け、sidecar 実行方式の確認、既知問題として README/issue コメントで暫定案内。

- #50 Speaker 2 Log generating error / #102 Volume check crashes with AttributeError: 'NoneType' object has no attribute 'close'
  理由: 音声関連の操作で即時エラー。古い #50 はコメント数も多く、未解決のまま再発している可能性が高い。
  推奨対応: 重複整理後に 1 件へ寄せて根本修正。回帰確認対象に追加。

- #98 [Bug]: VRCT is not opening for some reason / #90 [Bug]: app doesn't open at all
  理由: 起動不能は最重要。報告数は多くないが、発生したユーザーは完全に利用不能。
  推奨対応: ログ未生成時の診断手順を先に整備し、再現ログ収集を優先。

- #87 [Bug]: Transcriptor turbo models
  理由: マイクオフでもランダム文が送られる報告で、誤送信・スパムにつながる。コア機能の信頼性を損なう。
  推奨対応: turbo 系モデルを一時的に非推奨化するか、送信抑止のガードを検討。

### P1

- #63 [Bug]: Transcription Freezes with Google Engine in Bad Network
  理由: ネットワーク劣化時に文字起こし停止とトグル固着。通話中に詰まるタイプの不具合で影響が大きい。
  推奨対応: タイムアウト、再試行、状態復旧の見直し。

- #76 [Bug]: Most of time when i speak it fail to detect my voice and transcribe it
  理由: 文字起こし成功率の低下は主要価値に直結する。長期未解決でもある。
  推奨対応: デバイス条件、VAD 閾値、言語条件の切り分けを行う。

- #91 Error: undefined - Translation engine limit error
  理由: エラーメッセージが不明瞭で、復旧方法も見えない。翻訳基盤の失敗時 UX が悪い。
  推奨対応: エラー分類の改善と、レート制限時の案内/再試行設計を見直す。

- #104 [Feature]: Add a button to refresh tokens
  理由: 無料 API 利用時の復旧導線として実用性が高い。#91 に近い失敗体験の緩和策にもなる。
  推奨対応: 自動再試行より先に手動リフレッシュ導線を追加するのが小さく効く。

- #103 [Bug]: Lack of Speech Recognition Feedback Makes Debugging Difficult
  理由: 直接の障害ではないが、音声入力不調の自己診断を難しくしている。#76 などの切り分けにも効く。
  推奨対応: 入力レベル表示、認識状態表示、失敗理由の UI 露出を検討。

- #77 I downloaded it, but it's not used.
  理由: 配布・導入系の不具合の可能性がある。記述は曖昧だが、インストーラー/配置不良なら入口で離脱する。
  推奨対応: 追加情報依頼。再現できるなら P0 寄せ。

### P2

- #96 [Feature]: Add a simplified installation program
  理由: 導入障壁の低下は効果が高いが、不具合修正より後。
  推奨対応: 配布方式の改善案をまとめてから着手。

- #100 Can you add a custom server setting for speech recognition?
  理由: ローカル/LAN 逃がしは実益があるが、設計範囲が広い。
  推奨対応: まず translation 側の既存設定との整合を整理。

- #99 [Feature]: Is it possible to prevent it from automatically switching to Whisper?
  理由: 地域・接続条件依存だが、Whisper 自動切替による負荷増を避けたい要望は理解できる。
  推奨対応: 自動フォールバック無効化の設定追加を検討。

- #54 [Feature]: Limit transcribed message length In/Out
  理由: 誤認識時の表示崩れを抑える UX 改善。影響は明確で実装も比較的小さそう。
  推奨対応: 最大文字数と連続文字圧縮のどちらが有効かを先に決める。

- #92 Cannot build on linux, Failed to build 'SpeechRecognition'
  理由: 対象ユーザーは限定されるが、ビルド不能は開発体験として重い。コメントも多い。
  推奨対応: 正式サポート範囲を明示し、未サポートなら issue 上で明確化。対応するなら依存パッケージ固定を検討。

### P3

- #89 Custom API Address
  理由: 要望自体は価値が高いが、open PR #95 が対応中。
  推奨対応: PR レビュー優先。マージ後に issue を close できるか確認。

- #81 [Bug]: An error occurred, but it works properly
  理由: `in progress` 付きで、致命度も比較的低い。
  推奨対応: 既存作業の継続。

- #88 [Feature]: AMD GPU Support VIA RocM
  理由: 要望は妥当だが、実装・配布・検証コストが大きい。
  推奨対応: 需要観測を続け、設計調査タスクへ分離。

- #82 [Feature]: Support end-to-end multimodal translation with direct audio input
  理由: 戦略的には面白いが、大規模機能で現行不具合対応とは別レーン。
  推奨対応: 将来構想として別ドキュメント化。

- #97 [Feature]: Can “cohere transcribe” be added as well?
  理由: プロバイダ追加の 1 件。差し込み優先度は低い。
  推奨対応: 需要が複数件出るまで保留。

- #78 [Feature]: Support for HY-MT1.5-1.8B
  理由: モデル追加要望。既存不具合の解消より後。
  推奨対応: モデル追加要望をまとめて評価する。

- #75 [Feature]: Support for canary-qwen-2.5b
  理由: 同上。個別モデル追加としては後順位。
  推奨対応: #78 と同じキューにまとめる。

- #37 Feature Request: Verify Transcription and traduction upgrade to the newer SeamlessM4T Model
  理由: 技術調査枠。緊急性は低い。
  推奨対応: モデル戦略を見直す時に再評価。

- #27 Feature Request: SE on sending an OSC message
  理由: 価値はあるが、まずは誤送信を起こす既存バグ修正が先。
  推奨対応: OSC 周辺改善の束で扱う。

- #23 [Feature Request] Exclude word from translation
  理由: `in progress`。新規着手優先度は低い。
  推奨対応: 実装継続か、進捗が止まっているなら status 更新。

- #17 Feature Request: Use direct translation feature of whisper
  理由: 機能追加としては筋が良いが、今の backlog では後ろ。
  推奨対応: whisper 系改善の中で再検討。

- #93 [Feature]: (Please note that the title must be in English)
  理由: 要望内容が実質不明。
  推奨対応: 追加情報依頼後、反応がなければ close 候補。

## 直近の実行順

1. #94 の真偽確認と暫定アナウンス。
2. #50 / #102 の重複整理と root cause 調査。
3. #98 / #90 の起動不能調査テンプレ整備。
4. #87, #63, #76, #91 を「音声認識/翻訳の信頼性改善」束としてまとめて対処。
5. #104 と #103 を復旧導線・診断性改善として小さく拾う。
6. #89, #81, #23 は進行中扱いを維持しつつ棚卸し。

## 補足

- もし issue ラベル運用を強化するなら、`priority:p0` `priority:p1` `needs-info` `duplicate` `blocked-by-pr` を追加すると運用しやすい。
- 「モデル追加要望」は個別に捌かず、互換性・実装工数・需要をまとめて評価する backlog を別管理した方が良い。
- 追加で `decision:adopt` `decision:review` `decision:defer` `decision:reject` を置くと、「優先度は高いが今は実装しない」を表現しやすい。

## P1 コード調査メモ（2026-08-01）

コード変更は行わず、現在の `issue-p0` ブランチを対象に調査した。issue 起票時のリリースは #63 が 3.2.1、#76 が 3.3.2、#91 が 3.4.2、#103 が 3.4.3 であり、現在ブランチには文字起こし改善コミット `27418f3b` と `3c9e6f8f` が含まれる。そのため、起票時の症状と現在残っている問題を分けて扱う必要がある。

### #63 Google 文字起こしフリーズ

確度の高い原因候補:

- `models/transcription/transcription_transcriber.py` の Google 認識は `Recognizer.recognize_google()` を同期呼び出ししている。
- 導入済み SpeechRecognition 3.10.4.1 では、HTTP の timeout に `Recognizer.operation_timeout` を使用するが、現在の生成直後の値は `None`。応答を無期限に待つ可能性がある。
- 言語ごとの Google 認識例外は内側の `except Exception: pass` で握り潰され、ログにも UI にも失敗理由が出ない。
- `model.py` の `stopSpeakerTranscript()` は認識ワーカーを timeout なしで `join()` してから録音を止める。Google 呼び出しが戻らない場合、停止処理も完了しない。
- `controller.py` の受信停止処理も停止用スレッドを timeout なしで `join()` するため、speaker2Log トグルが固着する報告と整合する。

反証・再現確認:

- Google 認識開始後に接続を遮断または応答を遅延させ、停止要求が一定時間内に返るかを測る。
- `operation_timeout` を有限値にした場合だけ復旧するなら、HTTP 待機が主因と判断できる。

修正時の最小範囲:

- Google recognizer に有限の `operation_timeout` を設定する。
- `RequestError`、`UnknownValueError`、timeout を分類し、少なくともログへ残す。
- 録音停止を先に通知し、ワーカーの `join()` に上限を設ける。
- 低速・切断中の停止回帰テストを追加する。

### #91 `Error: undefined - Translation engine limit error`

確度の高い原因候補:

- 翻訳失敗時は `model.py` の `getTranslate()` が CTranslate2 へフォールバックし、`controller.py` の `changeToCTranslate2Process()` が元のオンラインエンジンを無効化する。この処理自体は実装済み。
- mic 翻訳経路だけ、失敗通知を旧形式 `{message, data}` で `/run/error_translation_engine` に送っている。
- UI の `useReceiveRoutes.js` は status 400 の応答に `result.error_code` を要求するため、mic 経路では `error_code` が `undefined` になる。
- speaker/chat 経路は `VRCTError.create_error_response(ErrorCode.TRANSLATION_ENGINE_LIMIT)` を使用しており、mic 経路だけ契約が不統一。
- `translation_translator.py` は翻訳バックエンドの全例外を `False` に変換するため、現在の `TRANSLATION_ENGINE_LIMIT` はレート制限だけでなく、通信障害やプロバイダ内部エラーも含む。

反証・再現確認:

- mic、speaker、chat の各経路で同じ翻訳失敗を発生させ、mic のみ `error_code` が欠落するか確認する。

修正時の最小範囲:

- mic 経路も統一エラーレスポンスへ変更し、契約テストを追加する。
- 次段階で翻訳失敗の理由を rate limit、network、authentication、provider error に分類する。

### #76 音声を認識しないことが多い

現行コードから確認できる点:

- マイクとスピーカーは現在、VAD が既定で有効。既定値は threshold 0.25、最小音声 64 ms、無音終了 768 ms、前方 padding 160 ms。
- VAD 有効時は `transcription_recorder.py` がデバイスストリームを直接読み、Silero VAD でセグメント化する。
- この経路では UI の `MIC_THRESHOLD` と `MIC_AUTOMATIC_THRESHOLD` が録音の採否に使われない。ユーザーが感度スライダーを変更しても、既定の VAD 経路には反映されない。
- Whisper では録音側 VAD に加え、推論時にも `vad_filter` が渡るため、二段階で音声が棄却される可能性がある。
- 現在ブランチには録音の正規化、VAD、partial segment、遅延計測の改善が入っているため、3.3.2 の報告がそのまま再現するとは限らない。

未確定事項:

- #76 の環境で VAD 前に音声が弱いのか、VAD で落ちるのか、Google/Whisper が結果を返さないのかはログがなく判別できない。
- 一律の VAD 閾値変更は誤送信を増やすため、実測前には行わない。

追加依頼する情報:

- 最新版での再現有無、入力デバイス名、Windows の入力レベル、マイク距離、失敗する発話の長さ。
- VAD 有効/無効、Google/Whisper の組み合わせごとの成功率。
- 可能なら同じ音声サンプルを現在の `evaluate_transcription.py` で比較する。

### #103 音声認識フィードバック不足

現在ブランチで追加済みのもの:

- VAD の segment ID、partial/final transcript、`inference_ms`、`audio_duration_ms` をバックエンドから UI へ送る経路がある。
- partial transcript の upsert/dismiss 用 UI ルートとテストがある。

現在も不足しているもの:

- 音声取得、VAD 判定、認識エンジン送信、認識成功/棄却を区別する状態表示がない。
- Google の言語ごとの失敗は握り潰されるため、失敗理由がログに残らない。
- 設定画面の音量メーターは文字起こし本体とは別 recorder を使用する。音量表示が動いても、実際の文字起こしパイプライン通過は保証しない。
- VAD 有効時には energy threshold が録音採否に使われないため、UI が実際の判定方式を正しく説明できていない。

判断:

- issue 全体が未実装という状態ではなく、partial 表示と基本メトリクスは先行対応済み。
- 残作業はエラー可視化、VAD 状態の観測、実パイプラインと一致した入力フィードバック。

#### 2026-08-03 issue本文確認と対応方針

issue本文（報告者 mikufilck、環境 Windows 11／中国、v3.4.3）を確認した。症状は「発話の多くが認識されない・再現条件が不明」で#76と重なるが、報告の焦点は「音声認識パイプラインのどの段階で失敗しているか分かるUIフィードバックが一切ない」点。ログ・スクリーンショットの提供はなし。

再現困難な「認識精度」そのものの原因調査は#76と同様に保留する。一方で「見える化」は再現ログがなくても着手できるため、次の範囲に限定して先行対応した。

- `AudioTranscriber`（[transcription_transcriber.py](../src-python/models/transcription/transcription_transcriber.py)）に `last_recognition_error` フラグを追加。Google認識で `UnknownValueError` 以外の例外（タイムアウト・`RequestError` など）が発生したら都度セットし、次呼び出し開始時にリセットする。
- `model.py` の `sendMicTranscript`/`sendSpeakerTranscript` がこのフラグを結果 dict に `recognition_error` として付加してコントローラへ渡す。
- `controller.py` の `micMessage`/`speakerMessage` が `recognition_error` を検知したら、新規エンドポイント `/run/transcription_recognition_error`（`word_filter` と同じシステムメッセージ表示経路）でユーザーに一過性通知を出す。
- フロントエンドは既存の `addSystemMessageLog_FromBackend` をそのまま再利用（[useReceiveRoutes.js](../src-ui/logics/useReceiveRoutes.js)）。

この対応により「認識エンジンへ送信したが失敗した」ことは可視化されたが、以下は引き続き未着手（別途仕様判断が必要な残作業として保留）。

- リアルタイム音量メーターと実際の文字起こしパイプラインの統合（現状は別recorder）。
- VAD判定（音声区間検出）の状態そのものの可視化。
- Whisperエンジン側の失敗可視化（今回はGoogleエンジンのみ対象）。

「発話が認識されない」というバグ本体（#76）は原因が判明してから再度着手する。

### #104 token refresh 導線

コード上の整理:

- Google/Bing の無料翻訳は、VRCT が更新可能な OAuth refresh token を保持しているわけではない。
- 翻訳失敗時に行っているのは、選択中オンラインエンジンの status を `False` にし、CTranslate2 へ切り替える処理。
- 起動時には各翻訳エンジンを並列に疎通・認証確認するが、実行中に同じ確認を再実行する共通エンドポイントはない。

仕様案:

- 表示名は「Refresh token」ではなく「Retry online translation engines」または「翻訳エンジンを再接続」が実態に近い。
- 操作時にオンラインエンジンを再疎通し、利用可能 status を更新する。
- 成功時に直前のエンジンへ自動で戻すか、選択肢へ復帰させるだけにするかは仕様決定が必要。
- #91 のエラー分類と同時に扱うと、再試行対象と待機時間を決めやすい。

#### 2026-08-03 issue本文確認と保留判断

issue本文（報告者 HenBian、2026-07-29、Windows 11／カナダ）を確認した。要望は「無料APIのレート制限で無効化されたプロバイダーを、再起動せずに再初期化できるボタンを設定画面に追加してほしい」というもの。「token」という語は実際の OAuth refresh token ではなく、上記の再疎通導線を指していると判断できる。issue自体は上記の仕様案どおりで、認識のズレはない。

現状のコード調査で、対象ロジックが `controller.py` の `init()`（起動時に一度だけ呼ばれるメソッド）内、[controller.py:3238-3419](../src-python/controller.py#L3238-L3419) に埋め込まれていることを確認した。翻訳エンジンごとの疎通・認証確認と `SELECTABLE_TRANSLATION_ENGINE_STATUS` 更新が約180行のクロージャとして書かれており、`init()` 以外から呼び出す手段がない。そのため実装するには次が必要になる。

- このブロックを `checkTranslationEnginesStatus()` 等の独立メソッドへ切り出す（`init()` からも新規エンドポイントからも呼べるようにするリファクタ）。
- 新規 run_mapping エンドポイント（例: `retry_translation_engines`）を追加し、結果を `translation_engines` / `selected_translation_engines` として UI へ再送信する。
- 連打防止のクールダウンを入れる。
- フロントエンドにボタンを追加し、`locales/*.yml` に文言を追加する。

単純なバグ修正ではなく、バックエンドのリファクタ＋新規エンドポイント＋フロントエンド＋多言語対応を伴う小規模機能追加と判断し、優先度は P1 のまま **保留（Defer）** とする。着手する場合は次の順序が扱いやすい。

1. `init()` 内の翻訳エンジンチェックブロックを独立メソッドへ切り出す（動作を変えないリファクタとして先に実施し、回帰確認する）。
2. 切り出したメソッドを呼ぶ再試行エンドポイントと連打防止を追加する。
3. #91 のエラー分類が先に整理されていれば、失敗理由に応じた再試行対象・待機時間の出し分けを検討する。
4. 表示名・成功時の挙動（自動復帰か選択肢復帰のみか）をUI実装前に決める。

### #77 インストール後に利用できない

コード上の配布方式:

- NSIS は `currentUser` install で、既定の配置先は `%LOCALAPPDATA%\VRCT`。
- インストーラーにアプリ一式を完全同梱せず、実行時に `https://huggingface.co/ms-software/VRCT/resolve/main/VRCT.zip` を取得して展開する。
- ダウンロード失敗時はインストールを `Abort` する。
- `VRCT.zip` は 2026-08-01 の調査時点で到達可能。release workflow も同じ asset を更新する設計。
- スタートメニューショートカットは作成される。デスクトップショートカットは GUI 上の選択または silent/passive オプションに依存する。

判断:

- 恒常的な asset 欠落より、地域・プロキシ・セキュリティ製品による Hugging Face ダウンロード失敗、またはデスクトップショートカットを「installation file」と表現している可能性が高い。
- 本文だけでは不具合か操作上の誤解か確定できないため `needs-info` が妥当。

追加依頼する情報:

- `%LOCALAPPDATA%\VRCT` の有無とファイル一覧。
- インストーラー詳細画面の最終メッセージ、AV の検疫履歴、Hugging Face URL へブラウザで到達できるか。
- スタートメニューから起動できるか、デスクトップアイコンだけがないのか。

### 調査時の検証

- `src-python` を import root にして `test_audio_pipeline.py`、`test_transcription_recorder.py`、`test_transcription_transcriber.py` を実行し、28 件すべて成功。
- Google の低速・切断、停止要求中のブロック、翻訳エラー形式は既存テストに含まれない。
- 調査中のコード変更なし。調査前から `.gitignore` に未コミット変更あり。

### 再開時の推奨順序

1. #63 に有限 timeout と停止回帰テストを追加する。
2. #91 の mic エラー形式を統一し、mic/speaker/chat の契約テストを追加する。
3. #91 と #104 をまとめ、オンライン翻訳エンジンの失敗分類と再接続仕様を決める。
4. 最新ブランチで #76 を再現し、VAD 前・VAD 後・認識後のどこで落ちるか計測する。
5. #103 は既存 partial 表示を前提に、VAD 状態と失敗理由の可視化へ範囲を絞る。
6. #77 は追加情報が来るまで `needs-info` とする。
