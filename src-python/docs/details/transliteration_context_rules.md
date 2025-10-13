# transliteration_context_rules.py - 文脈的転写ルールエンジン

## 概要

トークン化された結果に対して文脈依存の転写ルールを適用するコンパクトなルールエンジンです。隣接するトークンの情報に基づいて読み（かな）を動的に修正し、より自然で正確な転写を実現します。

## 主要機能

### 文脈依存転写
- 隣接トークン情報を利用した読み修正
- 優先度ベースのルール適用順序
- 正規表現・完全一致の両方に対応

### ルールエンジン
- 埋め込み型ルール定義（外部JSONファイル不要）
- 前方・後方の隣接トークン検査対応
- インプレース変更による効率的処理

### 動的読み変更
- 文脈に応じたかな読みの書き換え
- ひらがな・ヘボン式の自動クリア
- 呼び出し元での再計算トリガー

## ルール定義構造

### DEFAULT_RULES

```python
DEFAULT_RULES = {
    "rules": [
        {
            "name": "nan_next_tdna",           # ルール名
            "target": "何",                    # 対象文字
            "match_mode": "equals",            # マッチモード
            "direction": "next",               # 検査方向
            "kana_set": ["タ", "チ", "ツ"...], # 条件文字セット
            "on_true": {"kana": "ナン"},       # 条件真時のアクション
            "on_false": {"kana": "ナニ"}       # 条件偽時のアクション
        }
    ]
}
```

### ルール要素

#### 基本設定
- **name**: ルールの識別名
- **target**: 適用対象となる文字・文字列
- **priority**: 適用優先度（高い順に処理）
- **match_mode**: マッチングモード（"equals"/"regex"）

#### 条件設定
- **direction**: 隣接トークン検査方向（"next"/"prev"）
- **kana_set**: 条件判定用の文字セット
- **pattern**: 正規表現パターン（regex時）

#### アクション設定
- **on_true**: 条件成立時のアクション
- **on_false**: 条件不成立時のアクション
- **kana**: 設定する新しいかな読み

## 主要関数

### apply_context_rules

```python
def apply_context_rules(results: List[Dict[str, Any]], use_macron: bool = False) -> List[Dict[str, Any]]
```

文脈ルールをトークンリストに適用

#### パラメータ
- **results**: `Transliterator.split_kanji_okurigana`で生成されたトークン辞書のリスト
- **use_macron**: 互換性のためのパラメータ（ルール処理では未使用）

#### 戻り値
- **List[Dict[str, Any]]**: 修正されたトークンリスト（インプレース変更も実施）

#### 必須キー
各トークン辞書は以下のキーを含む必要があります：
- **orig**: 元の文字・文字列
- **kana**: かな読み
- **hira**: ひらがな表記
- **hepburn**: ヘボン式ローマ字

## 使用方法

### 基本的な文脈ルール適用

```python
from models.transliteration.transliteration_context_rules import apply_context_rules

# トークン化された結果（例）
results = [
    {"orig": "何", "kana": "ナニ", "hira": "なに", "hepburn": "nani"},
    {"orig": "度", "kana": "ド", "hira": "ど", "hepburn": "do"},
    {"orig": "も", "kana": "モ", "hira": "も", "hepburn": "mo"}
]

# 文脈ルールの適用
modified_results = apply_context_rules(results)

# 結果確認
for token in modified_results:
    print(f"{token['orig']}: {token['kana']} -> {token['hira']} ({token['hepburn']})")

# 期待される出力（「何度」の場合）:
# 何: ナン -> （再計算必要） （再計算必要）
# 度: ド -> ど (do)
# も: モ -> も (mo)
```

### カスタムルールでの処理

```python
# 独自ルール定義の例
custom_rules = {
    "rules": [
        {
            "name": "custom_rule_example",
            "target": "今",
            "match_mode": "equals",
            "direction": "next", 
            "kana_set": ["バ", "ビ", "ブ", "ベ", "ボ"],
            "priority": 100,
            "on_true": {"kana": "イマ"},
            "on_false": {"kana": "コン"}
        }
    ]
}

# 注意：現在の実装では DEFAULT_RULES が固定使用されています
# カスタムルールを使用するには関数の拡張が必要です
```

### 正規表現マッチングの例

```python
# 正規表現ルールの定義例
regex_rule = {
    "name": "kanji_pattern_rule",
    "match_mode": "regex",
    "pattern": r"^[一-龯]$",  # 任意の漢字1文字
    "direction": "next",
    "kana_set": ["ア", "イ", "ウ", "エ", "オ"],
    "priority": 50,
    "on_true": {"kana": "特殊読み"},
    "on_false": {"kana": "通常読み"}
}
```

### 転写パイプラインでの統合

```python
def complete_transliteration_pipeline(text):
    """完全な転写パイプライン"""
    
    # 1. 初期分割・転写
    transliterator = Transliterator()
    tokens = transliterator.split_kanji_okurigana(text)
    
    # 2. 文脈ルール適用
    tokens = apply_context_rules(tokens)
    
    # 3. 修正されたトークンの再計算
    for token in tokens:
        if token.get("kana") and not token.get("hira"):
            # ひらがな・ヘボン式の再計算
            token["hira"] = katakana_to_hiragana(token["kana"])
            token["hepburn"] = hiragana_to_hepburn(token["hira"])
    
    return tokens

# 使用例
text = "何度でも挑戦する"
result = complete_transliteration_pipeline(text)

for token in result:
    print(f"{token['orig']} -> {token['kana']} -> {token['hira']} -> {token['hepburn']}")
```

## ルール処理ロジック

### 処理フロー

1. **ルール準備**
   - 優先度の降順でソート
   - 正規表現の事前コンパイル

2. **トークン走査**
   - 各トークンに対してルールを順次適用
   - 空の`orig`を持つトークンはスキップ

3. **マッチング判定**
   - `equals`: 完全一致判定
   - `regex`: 正規表現マッチ判定

4. **隣接トークン検査**
   - `direction`に基づく隣接トークン特定
   - 空のトークンをスキップして有効トークンを検索

5. **条件評価**
   - 隣接トークンの`kana`の先頭文字チェック
   - `kana_set`との一致判定

6. **アクション実行**
   - 条件に応じて`on_true`/`on_false`を選択
   - `kana`の書き換えと`hira`/`hepburn`のクリア

### アルゴリズム詳細

```python
def process_token_with_rules(token_index, tokens, rules):
    """単一トークンのルール処理アルゴリズム"""
    
    token = tokens[token_index]
    orig = token.get("orig", "")
    
    # 空トークンはスキップ
    if not orig:
        return
    
    for rule in rules:  # 優先度順
        # マッチング判定
        if not matches_rule(orig, rule):
            continue
            
        # 隣接トークン検索
        neighbor = find_neighbor_token(token_index, tokens, rule["direction"])
        
        if neighbor:
            # 条件評価
            condition = evaluate_condition(neighbor, rule["kana_set"])
            
            # アクション実行
            action = rule["on_true"] if condition else rule["on_false"]
            apply_action(token, action)
            
            # 最初にマッチしたルールで処理終了
            break

def find_neighbor_token(current_index, tokens, direction):
    """隣接する有効トークンを検索"""
    
    if direction == "next":
        for i in range(current_index + 1, len(tokens)):
            if tokens[i].get("orig"):
                return tokens[i]
    elif direction == "prev":
        for i in range(current_index - 1, -1, -1):
            if tokens[i].get("orig"):
                return tokens[i]
    
    return None
```

## 具体的なルール例

### 「何」の読み分けルール

```python
{
    "name": "nan_next_tdna",
    "target": "何",
    "match_mode": "equals",
    "direction": "next",
    "kana_set": ["タ", "チ", "ツ", "テ", "ト", "ダ", "ヂ", "ヅ", "デ", "ド", "ナ", "ニ", "ヌ", "ネ", "ノ"],
    "on_true": {"kana": "ナン"},
    "on_false": {"kana": "ナニ"}
}
```

#### 動作例

```python
# 「何度」の場合
tokens = [
    {"orig": "何", "kana": "ナニ"},  # 初期状態
    {"orig": "度", "kana": "ド"}     # 次のトークン
]

# ルール適用後
tokens = [
    {"orig": "何", "kana": "ナン"},  # 「ド」が kana_set に含まれるため "ナン" に変更
    {"orig": "度", "kana": "ド"}
]

# 「何回」の場合  
tokens = [
    {"orig": "何", "kana": "ナニ"},  # 初期状態
    {"orig": "回", "kana": "カイ"}   # 次のトークン
]

# ルール適用後
tokens = [
    {"orig": "何", "kana": "ナニ"},  # 「カイ」が kana_set に含まれないため "ナニ" のまま
    {"orig": "回", "kana": "カイ"}
]
```

## エラーハンドリング

### 正規表現コンパイルエラー
```python
# 不正な正規表現の安全な処理
for rule in rules:
    if rule.get("match_mode") == "regex" and rule.get("pattern"):
        try:
            rule["_re"] = re.compile(rule["pattern"])
        except Exception as e:
            print(f"正規表現コンパイルエラー: {rule['pattern']} - {e}")
            rule["_re"] = None  # 無効化
```

### 不正なトークン構造
```python
# 必須キーの存在確認
def validate_token(token):
    """トークンの妥当性検証"""
    required_keys = ["orig", "kana", "hira", "hepburn"]
    
    for key in required_keys:
        if key not in token:
            print(f"警告: トークンに必須キー '{key}' が不足")
            token[key] = ""  # デフォルト値を設定
    
    return token
```

## パフォーマンス考慮事項

### 効率的な処理
- インプレース変更によるメモリ効率
- 優先度ソートによる早期終了
- 正規表現の事前コンパイル

### スケーラビリティ
- 大量トークンでの線形処理時間
- ルール数の増加に対する適切な対応
- キャッシュ機能の追加可能性

## 拡張可能性

### ルール形式の拡張
```python
# より複雑なルール例（将来的な拡張）
complex_rule = {
    "name": "multi_condition_rule",
    "target": "言",
    "conditions": [
        {"direction": "prev", "kana_set": ["オ", "コ"]},
        {"direction": "next", "kana_set": ["ハ", "バ"]}
    ],
    "operator": "AND",  # or "OR"
    "actions": {
        "all_true": {"kana": "ゴン"},
        "any_true": {"kana": "ゲン"},
        "all_false": {"kana": "イ"}
    }
}
```

### 動的ルール追加
```python
def add_runtime_rule(new_rule):
    """実行時ルール追加（拡張版）"""
    # ルールの検証
    if validate_rule_format(new_rule):
        DEFAULT_RULES["rules"].append(new_rule)
        return True
    return False
```

## 依存関係

### 必須依存関係
- `typing`: 型ヒント
- `re`: 正規表現処理

### 関連モジュール
- `transliteration_transliterator.py`: メイン転写クラス
- `transliteration_kana_to_hepburn.py`: かな→ヘボン式変換

## 注意事項

- ルール適用後は`hira`と`hepburn`が空文字列になるため、呼び出し元での再計算が必要
- 現在のルールは日本語に特化している
- ルール適用順序は優先度に依存するため、適切な設定が重要
- 正規表現ルールはパフォーマンスに影響する可能性がある

## 将来の改善点

- 外部ルールファイルの読み込み対応
- より複雑な条件式のサポート
- ルール適用ログ・デバッグ機能
- 言語別ルールセットの対応
- パフォーマンス最適化とキャッシュ機能