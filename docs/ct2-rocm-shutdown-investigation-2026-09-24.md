# CTranslate2 ROCm Windows 終了ハング調査

調査日: 2026-09-24

## 結論

CTranslate2 4.8.2 の Windows ROCm wheel は、CPU 推論だけでも推論後の
プロセス終了時にハングする。標準版 CTranslate2 4.8.2 では同じ条件で
正常終了する。

このため、現時点では AMD 版の配布を保留する。`unload_model(False)`、
`del`、`gc.collect()`、ROCm runtime DLL の修正版差し替えだけでは解決しない。

## 再現結果

同じ Python 3.11、モデル、CTranslate2 4.8.2 で比較した。

| 環境 | デバイス | 推論 | 結果 |
| --- | --- | --- | --- |
| 標準 wheel | CPU / float32 | あり | 正常終了、exit 0 |
| ROCm wheel | CPU / float32 | あり | `gc_done` 後に180秒超過、exit 124 |
| ROCm wheel | CPU / float32 | なし | 正常終了、exit 0 |

したがって、Radeon のカーネル実行そのものではなく、ROCm build に含まれる
native state と終了処理の組み合わせがトリガーと考えられる。

## 実施した検証

- ROCm wheel の `amdhip64_7.dll` を ROCm runtime の修正版へ差し替えた。
  CPU 推論後のハングは継続したため、既知の Windows runtime teardown 修正
  だけでは CTranslate2 の再現を解消できない。
- HIP DLL の `/DELAYLOAD` 化を試した。PE の通常 import から HIP DLL を外す
  ことはできたが、実行時の DLL ロードは WinError 1114 で失敗した。
- `ReplicaWorker::finalize()` の replica reset 前に stream 同期を追加する
  CTranslate2 修正候補をビルドした。CPU-only 再現に対する効果は未成立で、
  GPU teardown の候補と位置付ける。
- CTranslate2 の CPU core と HIP backend を別 DLL に分離する設計案を検討した。
  CPU 実行時に HIP runtime を import・初期化しない構成が、根本的な候補になる。

## `model.model = None` の適用範囲

faster-whisper の `WhisperModel` には、native CTranslate2 Whisper object を
切り離す暫定回避策として次が考えられる。

```python
whisper_model = self.whisper_model
if whisper_model is not None:
    whisper_model.model = None
self.whisper_model = None
```

これは文字起こし側の非公開内部属性に依存するため、文字起こし worker の停止と
実行中の推論完了を確認した後だけで実行する。native resource の正式な解放 API
ではなく、将来の faster-whisper 更新で壊れる可能性もある。

一方、翻訳側の `self.ctranslate2_translator` は直接の
`ctranslate2.Translator` であり、faster-whisper の `WhisperModel` とは構造が
異なる。この `model.model = None` は翻訳側の CTranslate2 終了ハングには
適用できない。

## 判断と upstream への報告方針

現時点の方針は AMD 版配布保留とする。

upstream には次を報告する。

1. ROCm wheel は CPU 推論後にも終了ハングする最小再現
2. 標準 wheel との比較結果
3. ROCm runtime 修正版 DLL の A/B でも未解消だったこと
4. CPU core と HIP backend の DLL 分離、または CPU 実行時の HIP 初期化抑制の提案
5. GPU 実機での teardown 検証が別途必要であること

`TerminateProcess` は通常の cleanup には使わず、ハングした子プロセスの検証用
タイムアウト処理に限定する。