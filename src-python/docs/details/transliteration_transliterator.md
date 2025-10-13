# transliteration_transliterator.py - 総合音写・転写システム

## 概要

SudachiPyを利用した日本語のローマ字転写システムのメインクラスです。形態素解析、漢字・送り仮名の分離、文脈依存ルールの適用、ヘボン式変換を統合し、高精度な日本語ローマ字化を提供します。

## 主要機能

### 統合転写システム
- SudachiPyによる高精度形態素解析
- 漢字・送り仮名の自動分離処理
- 文脈依存読み変更ルールの適用

### 多層変換処理
- カタカナ読み取得・分配
- ひらがな自動変換
- ヘボン式ローマ字生成

### 並行処理対応
- スレッドセーフなトークナイザー利用
- ロック機構による安全な並行実行
- 高負荷環境での安定動作

## クラス構造

### Transliterator クラス
```python
class Transliterator:
    def __init__(self) -> None:
        self.tokenizer_obj: tokenizer.Tokenizer
        self.mode: tokenizer.Tokenizer.SplitMode
        self._tokenizer_lock: threading.Lock
```

日本語転写処理の中核クラス

#### 属性
- **tokenizer_obj**: SudachiPyトークナイザーインスタンス
- **mode**: 分割モード（SplitMode.C = 最長一致）
- **_tokenizer_lock**: 並行アクセス制御用ミューテックス

## 主要メソッド

### analyze

```python
def analyze(self, text: str, use_macron: bool = False) -> List[Dict[str, Any]]
```

テキストを解析して転写情報を生成

#### パラメータ
- **text**: 解析対象の日本語テキスト
- **use_macron**: マクロン使用フラグ（長音表記方式）

#### 戻り値
- **List[Dict[str, Any]]**: トークン転写情報のリスト

#### 出力辞書構造
```python
{
    "orig": str,      # 元の文字・文字列
    "kana": str,      # カタカナ読み
    "hira": str,      # ひらがな読み  
    "hepburn": str    # ヘボン式ローマ字
}
```

### split_kanji_okurigana (静的メソッド)

```python
@staticmethod
def split_kanji_okurigana(surface: str, reading_kana: str, use_macron: bool = True) -> List[Dict[str, str]]
```

単語の表層形と読みを漢字・送り仮名ブロックに分割

#### パラメータ
- **surface**: 表層形（漢字+ひらがな混在可能）
- **reading_kana**: 全体のカタカナ読み
- **use_macron**: ヘボン式変換でのマクロン使用

#### 戻り値
- **List[Dict[str, str]]**: 分割された部分の転写情報

## 補助メソッド

### is_kanji (静的メソッド)

```python
@staticmethod 
def is_kanji(ch: str) -> bool
```

文字が漢字かどうかを判定

#### パラメータ
- **ch**: 判定対象文字

#### 戻り値
- **bool**: 漢字判定結果

### kata_to_hira (静的メソッド)

```python
@staticmethod
def kata_to_hira(text: str) -> str
```

カタカナをひらがなに変換

#### パラメータ
- **text**: 変換対象のカタカナテキスト

#### 戻り値
- **str**: ひらがな変換結果

## 使用方法

### 基本的な転写処理

```python
from models.transliteration.transliteration_transliterator import Transliterator

# 転写システムの初期化
transliterator = Transliterator()

# 基本的な文章の転写
text = "向こうへ行く"
results = transliterator.analyze(text)

for token in results:
    print(f"{token['orig']} -> {token['kana']} -> {token['hira']} -> {token['hepburn']}")

# 期待される出力例:
# 向こう -> ムコウ -> むこう -> mukou
# へ -> ヘ -> へ -> he  
# 行く -> イク -> いく -> iku
```

### マクロン使用の長音処理

```python
# マクロンを使用した長音表記
text = "東京に行く"
results_macron = transliterator.analyze(text, use_macron=True)
results_normal = transliterator.analyze(text, use_macron=False)

print("=== マクロンあり ===")
for token in results_macron:
    print(f"{token['orig']} -> {token['hepburn']}")

print("=== マクロンなし ===")  
for token in results_normal:
    print(f"{token['orig']} -> {token['hepburn']}")

# 期待される出力:
# === マクロンあり ===
# 東京 -> tōkyō
# に -> ni
# 行く -> iku

# === マクロンなし ===  
# 東京 -> toukyou
# に -> ni
# 行く -> iku
```

### 複雑な文章の処理

```python
# 漢字・ひらがな・カタカナ・英語混在文の処理
complex_text = "パーティーで美しい花を見る"
results = transliterator.analyze(complex_text, use_macron=True)

for token in results:
    print(f"原文: '{token['orig']}'")
    print(f"  カナ: {token['kana']}")
    print(f"  ひら: {token['hira']}")  
    print(f"  ローマ: {token['hepburn']}")
    print()

# 期待される出力:
# 原文: 'パーティー'
#   カナ: パーティー
#   ひら: ぱーてぃー
#   ローマ: pātī
# 
# 原文: 'で'  
#   カナ: デ
#   ひら: で
#   ローマ: de
# 
# 原文: '美しい'
#   カナ: ウツクシイ
#   ひら: うつくしい
#   ローマ: utsukushii
```

### 文脈依存ルールの効果確認

```python
# 文脈に依存する読み変更の例（「何」の読み分け）
test_cases = [
    "何が好き？",      # 何 -> ナニ (後続が「ガ」)
    "何度も挑戦",      # 何 -> ナン (後続が「ド」)
    "何色ありますか？"   # 何 -> ナニ (後続が「イ」)
]

for text in test_cases:
    results = transliterator.analyze(text)
    
    print(f"入力: {text}")
    
    # 「何」トークンを探して読みを確認
    for token in results:
        if token['orig'] == '何':
            print(f"「何」の読み: {token['kana']} -> {token['hepburn']}")
            break
    print()

# 期待される出力:
# 入力: 何が好き？
# 「何」の読み: ナニ -> nani
#
# 入力: 何度も挑戦
# 「何」の読み: ナン -> nan
#
# 入力: 何色ありますか？
# 「何」の読み: ナニ -> nani
```

### 特殊文字・記号の処理

```python
# 記号・英数字混在テキストの処理
mixed_text = "ID：12345、URL：https://example.com"
results = transliterator.analyze(mixed_text)

for token in results:
    print(f"'{token['orig']}' -> '{token['hepburn']}'")

# 期待される出力:
# 'ID' -> 'ID'           # 英字はそのまま
# '：' -> '：'           # 記号はそのまま  
# '12345' -> '12345'     # 数字はそのまま
# '、' -> '、'           # 区切り記号はそのまま
# 'URL' -> 'URL'         # 英字はそのまま
```

## 内部処理フロー

### 解析処理パイプライン

```python
def analyze_pipeline_explained(self, text):
    """転写処理パイプラインの詳細説明"""
    
    # 1. SudachiPy形態素解析
    with self._tokenizer_lock:
        tokens = self.tokenizer_obj.tokenize(text, self.mode)
    
    results = []
    
    # 2. 各トークンの処理
    for token in tokens:
        surface = token.surface()        # 表層形
        reading = token.reading_form()   # 読み（カタカナ）
        pos = token.part_of_speech()    # 品詞情報
        
        # 3. 記号・空白の特別処理
        if pos and pos[0] in ["記号", "補助記号", "空白"]:
            reading = surface  # 記号は表層形をそのまま使用
        
        # 4. 表層形と読みが同じ場合（ひらがな・記号等）
        if surface == reading:
            results.append({
                "orig": surface,
                "kana": reading,
                "hira": surface,      # そのまま
                "hepburn": surface    # そのまま
            })
            continue
        
        # 5. 単一文字の処理
        if len(surface) == 1:
            results.append({
                "orig": surface,
                "kana": reading,
                "hira": self.kata_to_hira(reading),
                "hepburn": katakana_to_hepburn(reading, use_macron)
            })
        else:
            # 6. 複数文字の漢字・送り仮名分離
            parts = self.split_kanji_okurigana(surface, reading, use_macron)
            results.extend(parts)
    
    # 7. 文脈依存ルールの適用
    try:
        results = apply_context_rules(results, use_macron) or results
    except Exception:
        pass  # ルール適用失敗時は元の結果を使用
    
    # 8. ルール適用後の再計算
    for entry in results:
        kana = entry.get("kana", "")
        if kana:
            entry["hira"] = self.kata_to_hira(kana)
            entry["hepburn"] = katakana_to_hepburn(kana, use_macron)
    
    return results
```

### 漢字・送り仮名分離アルゴリズム

```python
def split_algorithm_explained(surface, reading_kana):
    """分離アルゴリズムの詳細説明"""
    
    # 1. 表層形のブロック分割
    blocks = []
    current_block = ""
    prev_is_kanji = None
    
    for char in surface:
        is_kanji = Transliterator.is_kanji(char)
        
        if prev_is_kanji is None or is_kanji == prev_is_kanji:
            # 同じタイプの文字は同じブロックに
            current_block += char
        else:
            # タイプが変わったら新しいブロック
            blocks.append((prev_is_kanji, current_block))
            current_block = char
        
        prev_is_kanji = is_kanji
    
    if current_block:
        blocks.append((prev_is_kanji, current_block))
    
    # 例: "向こう" -> [(True, "向"), (False, "こう")]
    #     "行く" -> [(True, "行"), (False, "く")]
    
    # 2. 読みの分配
    kana_len = len(reading_kana)
    
    # 初期割当: 各ブロックの文字数に比例
    allocations = [len(block_text) for _, block_text in blocks]
    allocated_total = sum(allocations)
    remaining = kana_len - allocated_total
    
    # 3. 余った読みの分配（漢字ブロック優先）
    if remaining > 0:
        # まず漢字ブロックに分配
        for i, (is_kanji, _) in enumerate(blocks):
            if remaining <= 0:
                break
            if is_kanji:
                allocations[i] += 1
                remaining -= 1
        
        # まだ余りがある場合は左から順に分配
        i = 0
        while remaining > 0 and len(blocks) > 0:
            allocations[i] += 1
            remaining -= 1
            i = (i + 1) % len(blocks)
    
    # 4. 読みが不足している場合は右から削減
    if remaining < 0:
        need_to_remove = -remaining
        i = len(blocks) - 1
        
        while need_to_remove > 0 and i >= 0:
            can_remove = max(0, allocations[i] - 1)
            remove_amount = min(can_remove, need_to_remove)
            allocations[i] -= remove_amount
            need_to_remove -= remove_amount
            i -= 1
    
    # 5. 最終的な読み分配
    pos = 0
    result = []
    
    for (is_kanji, block_text), allocation in zip(blocks, allocations):
        block_reading = reading_kana[pos:pos + allocation]
        pos += allocation
        
        result.append({
            "orig": block_text,
            "kana": block_reading,
            "hira": Transliterator.kata_to_hira(block_reading),
            "hepburn": katakana_to_hepburn(block_reading, use_macron)
        })
    
    return result
```

## 並行処理・スレッドセーフティ

### ロック機構

```python
class ThreadSafeUsage:
    """スレッドセーフな使用例"""
    
    def __init__(self):
        self.transliterator = Transliterator()
    
    def process_texts_concurrently(self, texts):
        """複数テキストの並行処理"""
        import concurrent.futures
        
        def process_single(text):
            return self.transliterator.analyze(text)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # 内部のロック機構により安全に並行実行
            futures = [executor.submit(process_single, text) for text in texts]
            results = [f.result() for f in futures]
        
        return results

# 使用例
processor = ThreadSafeUsage()
texts = ["東京に行く", "大阪で食事", "名古屋を観光", "福岡に宿泊"]
results = processor.process_texts_concurrently(texts)

for i, result in enumerate(results):
    print(f"テキスト{i+1}: {texts[i]}")
    for token in result:
        print(f"  {token['orig']} -> {token['hepburn']}")
```

### パフォーマンス考慮事項

```python
# 大量テキスト処理のベストプラクティス
def efficient_batch_processing(texts, batch_size=100):
    """効率的なバッチ処理"""
    
    transliterator = Transliterator()
    results = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        batch_results = []
        for text in batch:
            # 各テキストを個別に処理（ロック制御あり）
            result = transliterator.analyze(text)
            batch_results.append(result)
        
        results.extend(batch_results)
        
        # バッチ間で少し休憩（メモリ管理）
        if len(results) % 1000 == 0:
            print(f"処理済み: {len(results)} テキスト")
    
    return results
```

## エラーハンドリング

### 例外処理

```python
def safe_analyze(text):
    """安全な解析処理"""
    
    transliterator = Transliterator()
    
    try:
        results = transliterator.analyze(text)
        return results, None
        
    except RuntimeError as e:
        if "Already borrowed" in str(e):
            # SudachiPyの並行アクセスエラー
            print("並行アクセスエラーが発生しました。リトライします。")
            return None, "RETRY_NEEDED"
        else:
            print(f"実行時エラー: {e}")
            return None, "RUNTIME_ERROR"
            
    except Exception as e:
        print(f"予期しないエラー: {e}")
        return None, "UNKNOWN_ERROR"

# 使用例（リトライ機構付き）
def analyze_with_retry(text, max_retries=3):
    """リトライ機構付き解析"""
    
    for attempt in range(max_retries):
        results, error = safe_analyze(text)
        
        if results is not None:
            return results
        
        if error == "RETRY_NEEDED":
            print(f"リトライ {attempt + 1}/{max_retries}")
            import time
            time.sleep(0.1 * (attempt + 1))  # 指数バックオフ
            continue
        else:
            break
    
    # 全てのリトライが失敗した場合のフォールバック
    print("解析に失敗しました。フォールバック処理を実行します。")
    return [{"orig": text, "kana": text, "hira": text, "hepburn": text}]
```

## 設定・カスタマイズ

### SudachiPy設定

```python
# カスタムSudachiPy設定での初期化
class CustomTransliterator(Transliterator):
    def __init__(self, dict_type="full", split_mode="C"):
        """カスタム設定での初期化"""
        
        # 辞書タイプの選択
        dict_types = {
            "small": dictionary.Dictionary.create(dict_type="small"),
            "core": dictionary.Dictionary.create(dict_type="core"), 
            "full": dictionary.Dictionary.create(dict_type="full")
        }
        
        self.tokenizer_obj = dict_types.get(dict_type, dict_types["full"])
        
        # 分割モードの選択
        split_modes = {
            "A": tokenizer.Tokenizer.SplitMode.A,  # 短い単位
            "B": tokenizer.Tokenizer.SplitMode.B,  # 中間単位
            "C": tokenizer.Tokenizer.SplitMode.C   # 長い単位（デフォルト）
        }
        
        self.mode = split_modes.get(split_mode, split_modes["C"])
        self._tokenizer_lock = threading.Lock()

# 使用例
# 短い単位での分割を使用
small_unit_transliterator = CustomTransliterator(dict_type="core", split_mode="A")

text = "取り敢えず検索してみる"
results = small_unit_transliterator.analyze(text)

for token in results:
    print(f"{token['orig']} -> {token['hepburn']}")
```

## テスト・デバッグ

### 包括的テストセット

```python
def run_comprehensive_tests():
    """包括的な機能テスト"""
    
    transliterator = Transliterator()
    
    test_cases = [
        # 基本的な文章
        ("向こうへ行く", "向こう", "ムコウ"),
        ("美しい花", "美しい", "ウツクシイ"),
        
        # 文脈依存
        ("何度も", "何", "ナン"), 
        ("何が", "何", "ナニ"),
        
        # 外来語
        ("パーティー", "パーティー", "パーティー"),
        ("コンピューター", "コンピューター", "コンピューター"),
        
        # 漢字・送り仮名
        ("取り敢えず", "取り", "トリ"),
        ("見知らぬ", "見知ら", "ミシラ"),
        
        # 記号・英数字
        ("ID：12345", "ID", "ID"),
        ("SessionIDを取得", "SessionID", "SessionID")
    ]
    
    for text, target_orig, expected_kana in test_cases:
        results = transliterator.analyze(text)
        
        # 対象トークンを検索
        target_token = None
        for token in results:
            if token['orig'] == target_orig:
                target_token = token
                break
        
        if target_token:
            actual_kana = target_token['kana']
            status = "✓" if actual_kana == expected_kana else "✗"
            print(f"{status} {text}: {target_orig} -> {actual_kana} (期待値: {expected_kana})")
        else:
            print(f"✗ {text}: トークン '{target_orig}' が見つかりません")

run_comprehensive_tests()
```

## 依存関係

### 必須依存関係
- `sudachipy`: 形態素解析エンジン
- `threading`: 並行制御
- `typing`: 型ヒント

### 内部モジュール依存
- `transliteration_kana_to_hepburn`: ヘボン式変換
- `transliteration_context_rules`: 文脈依存ルール

### システム要件
- Python 3.7以上
- SudachiPy辞書ファイル（自動ダウンロード）
- 十分なメモリ（辞書読み込み用）

## 注意事項・制限

### 処理精度の制限
- 形態素解析結果に依存
- 未知語・固有名詞は読み推定
- 文脈によっては不正確な分割

### パフォーマンス制限
- 初回実行時の辞書読み込み時間
- 大量テキスト処理時のメモリ使用量
- 並行アクセス時のロック待機

### 出力形式の制限
```python
# 現在サポートしていない機能
unsupported_features = [
    "アクセント記号（音調）",
    "方言・古語の特殊読み",
    "人名・地名の特殊読み",
    "外国語の音写（中国語・韓国語等）",
    "カスタム読み辞書",
    "品詞情報の出力"
]
```

## 関連モジュール

- `transliteration_kana_to_hepburn.py`: ヘボン式変換処理
- `transliteration_context_rules.py`: 文脈依存ルール適用
- `config.py`: システム設定管理
- `utils.py`: ユーティリティ関数

## 将来の改善点

- カスタム読み辞書対応
- より高精度な文脈解析
- 他言語音写システムとの統合
- リアルタイム処理最適化
- 分散処理対応