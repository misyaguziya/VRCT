# test_endpoints.py - APIエンドポイントテストモジュール

## 概要
VRCTアプリケーションのAPIエンドポイントを包括的にテストするためのモジュールです。メインループの各種機能をランダムアクセスでテストし、システムの安定性と堅牢性を検証します。

### 2025-10 更新点（commit a54538e 反映）

動的値が必要な `/set/data/*` エンドポイントに対し、事前に対応する `/get/data/...` エンドポイントを呼び出して最新値を取得し、`self.config_dict` にキャッシュしてからランダム選択する方式に変更しました。これにより以下が改善されています:

- 翻訳/転写エンジン選択時の存在しないキー送信防止
- 計算デバイス / 重みタイプ選択の安定化（リスト更新後に選択）
- マイク/スピーカー関連タイムアウト値の正常範囲チェック（取得した最新値を基準にバリデーション）
- Whisper / CTranslate2 重みタイプ辞書のキー集合変化への追従

例: `"/set/data/selected_translation_engines"` 試験前に `"/get/data/selectable_translation_engines"` を呼び、取得したリストから `random.choice()`。従来の初期キャッシュ依存から、実行時取得へ移行。

## 主要機能

### Color クラス

- ANSIエスケープシーケンスを使用したコンソール出力色彩管理
- テスト結果の視覚的表示（成功・失敗・スキップ等）

### TestMainloop クラス

- APIエンドポイントの包括的テスト実行
- ランダムアクセステスト
- テスト結果の記録・分析
- VRCTメインループとの統合テスト

## 主要メソッド

### テスト実行メソッド

- `test_endpoints_on_off_all()`: ON/OFF系エンドポイントの全テスト
- `test_set_data_endpoints_all()`: データ設定系エンドポイントの全テスト
- `test_run_endpoints_all()`: 実行系エンドポイントの全テスト
- `test_endpoints_all_random()`: 全エンドポイントのランダムアクセステスト

### 特定機能テスト

- `test_translate_all_language_pairs()`: 全言語ペアでの翻訳テスト
- `test_endpoints_on_off_continuous()`: ON/OFF連続切り替えテスト
- `test_endpoints_specific_random()`: 特定エンドポイントのランダムテスト

### 結果分析

- `generate_summary()`: テスト結果のサマリー生成
- `record_test_result()`: テスト結果の記録

## 使用方法

### 基本的な使い方

```python
# テストインスタンスを作成
test = TestMainloop()

# 各種テストを実行
test.test_endpoints_on_off_all()
test.test_set_data_endpoints_all()
test.test_run_endpoints_all()

# テスト結果のサマリー表示
test.generate_summary()
```

### ランダムテストの実行

```python
# 全エンドポイントのランダムアクセステスト
test.test_endpoints_all_random()

# 特定エンドポイントのランダムテスト
test.test_endpoints_specific_random()
```

## 依存関係

- `mainloop`: VRCTメインループモジュール
- `random`: ランダムテストデータ生成
- `time`: テスト間隔制御

## テスト対象エンドポイント

### 制御系

- `/set/enable/*`: 機能有効化
- `/set/disable/*`: 機能無効化

### データ設定系

- `/set/data/*`: 各種設定データの更新

動的取得対象（代表例）:

- `selected_translation_engines` → `/get/data/selectable_translation_engines`
- `selected_transcription_engine` → `/get/data/selectable_transcription_engines`
- `selected_translation_compute_device` → `/get/data/selectable_translation_compute_device_list`
- `ctranslate2_weight_type` → `/get/data/selectable_ctranslate2_weight_type_dict`
- `whisper_weight_type` → `/get/data/selectable_whisper_weight_type_dict`
- `selected_mic_host` / `selected_mic_device` → `/get/data/selectable_mic_host_list` / `/get/data/selectable_mic_device_list`
- `selected_speaker_device` → `/get/data/selectable_speaker_device_list`

### 実行系

- `/run/*`: 各種機能の実行

### データ削除系

- `/delete/data/*`: データの削除

## 注意事項

- テスト実行前に`config.json`を削除して初期化
- 重いAIモデルを使用するテストは実行時間に注意
- ランダムテストは指定回数（デフォルト1000-10000回）実行される
- テスト終了時は自動的にすべての機能を無効化する

## エラーハンドリング

- 各テストは独立して実行され、一つの失敗が全体に影響しない
- 期待されるステータスコードと実際の結果を比較
- VRAM不足等のリソースエラーも適切にハンドリング

## テスト結果の分類

- **PASS**: 期待されるステータスコードと一致
- **ERROR**: 期待されるステータスコードと不一致
- **SKIP**: テスト実行不可（401ステータス）
- **Invalid**: 無効なエンドポイント（404ステータス）
