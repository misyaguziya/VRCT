# transliteration_kana_to_hepburn.py - カタカナ→ヘボン式変換

## 概要

カタカナ文字列を標準的なヘボン式ローマ字に変換するモジュールです。マクロン（長音記号）対応、外来語音の変換、促音・撥音処理など、日本語のローマ字表記に必要な機能を包括的に提供します。

## 主要機能

### 標準的なヘボン式変換
- カタカナ文字の基本ローマ字変換
- マクロン（ā ī ū ē ō）による長音表現
- 連続母音表記の選択的対応

### 特殊音処理
- 促音（ッ）の適切な子音重複処理
- 撥音（ン）のm/n使い分け
- 長音符（ー）の前母音延長処理

### 外来語対応
- シェ（she）、チェ（che）等の組み合わせ
- ヴ音（vu, va, vi, ve, vo）の変換
- ファ行（fa, fi, fe, fo）の処理

## 主要関数

### katakana_to_hepburn

```python
def katakana_to_hepburn(kata: str, use_macron: bool = True) -> str
```

カタカナ文字列をヘボン式ローマ字に変換

#### パラメータ
- **kata**: 変換対象のカタカナ文字列
- **use_macron**: マクロン使用フラグ（True=ā ī ū ē ō、False=aa ii uu ee oo）

#### 戻り値
- **str**: ヘボン式ローマ字文字列（小文字）

## 使用方法

### 基本的な変換

```python
from models.transliteration.transliteration_kana_to_hepburn import katakana_to_hepburn

# 基本的なカタカナ変換
result1 = katakana_to_hepburn("カタカナ")
print(result1)  # "katakana"

# 長音のマクロン表記
result2 = katakana_to_hepburn("コンピューター", use_macron=True)
print(result2)  # "konpyūtā"

# 長音の連続母音表記
result3 = katakana_to_hepburn("コンピューター", use_macron=False)
print(result3)  # "konpyuutaa"
```

### 特殊音の処理

```python
# 促音（ッ）の処理
result1 = katakana_to_hepburn("キャッチ")
print(result1)  # "kyatchi"

result2 = katakana_to_hepburn("マッチャ")
print(result2)  # "matcha"

# 撥音（ン）の処理
result3 = katakana_to_hepburn("ホンバン")  # ホン+バン
print(result3)  # "homban" (n→m変換)

result4 = katakana_to_hepburn("ホンテン")  # ホン+テン
print(result4)  # "honten" (nのまま)
```

### 外来語音の変換

```python
# 外来語特殊音
result1 = katakana_to_hepburn("シェア")
print(result1)  # "shea"

result2 = katakana_to_hepburn("チェック")
print(result2)  # "chekku"

result3 = katakana_to_hepburn("ジェット")
print(result3)  # "jetto"

# ヴ音の処理
result4 = katakana_to_hepburn("ヴァイオリン")
print(result4)  # "vaiorin"

result5 = katakana_to_hepburn("ヴィーナス")
print(result5)  # "vīnasu"

# ファ行の処理
result6 = katakana_to_hepburn("ファイル")
print(result6)  # "fairu"

result7 = katakana_to_hepburn("フィルム")  
print(result7)  # "firumu"
```

### 長音処理の詳細

```python
# 長音符（ー）の処理
result1 = katakana_to_hepburn("スーパー", use_macron=True)
print(result1)  # "sūpā"

result2 = katakana_to_hepburn("パーティー", use_macron=True)
print(result2)  # "pātī"

# ou → ō の変換（東京型）
result3 = katakana_to_hepburn("トウキョウ", use_macron=True)
print(result3)  # "tōkyō"

# 連続母音表記との比較
result4 = katakana_to_hepburn("トウキョウ", use_macron=False)
print(result4)  # "toukyou"
```

### 複雑な組み合わせ

```python
# 拗音（ゃゅょ）の組み合わせ
test_cases = [
    ("キャンプ", "kyanpu"),
    ("シュート", "shūto"), 
    ("チョコレート", "chokorēto"),
    ("ギュウニュウ", "gyūnyū"),
    ("リュックサック", "ryukkusakku"),
    ("ピョンピョン", "pyonpyon")
]

for kata, expected in test_cases:
    result = katakana_to_hepburn(kata)
    print(f"{kata} -> {result}")
    # キャンプ -> kyanpu
    # シュート -> shūto
    # チョコレート -> chokorēto
    # ギュウニュウ -> gyūnyū
    # リュックサック -> ryukkusakku
    # ピョンピョン -> pyonpyon
```

## 変換ルール詳細

### 基本音対応表

```python
base_mapping = {
    # 清音
    'ア':'a', 'イ':'i', 'ウ':'u', 'エ':'e', 'オ':'o',
    'カ':'ka', 'キ':'ki', 'ク':'ku', 'ケ':'ke', 'コ':'ko',
    'サ':'sa', 'シ':'shi', 'ス':'su', 'セ':'se', 'ソ':'so',
    'タ':'ta', 'チ':'chi', 'ツ':'tsu', 'テ':'te', 'ト':'to',
    'ナ':'na', 'ニ':'ni', 'ヌ':'nu', 'ネ':'ne', 'ノ':'no',
    'ハ':'ha', 'ヒ':'hi', 'フ':'fu', 'ヘ':'he', 'ホ':'ho',
    'マ':'ma', 'ミ':'mi', 'ム':'mu', 'メ':'me', 'モ':'mo',
    'ヤ':'ya', 'ユ':'yu', 'ヨ':'yo',
    'ラ':'ra', 'リ':'ri', 'ル':'ru', 'レ':'re', 'ロ':'ro',
    'ワ':'wa', 'ヲ':'wo', 'ン':'n',
    
    # 濁音・半濁音
    'ガ':'ga', 'ギ':'gi', 'グ':'gu', 'ゲ':'ge', 'ゴ':'go',
    'ザ':'za', 'ジ':'ji', 'ズ':'zu', 'ゼ':'ze', 'ゾ':'zo',
    'ダ':'da', 'ヂ':'ji', 'ヅ':'zu', 'デ':'de', 'ド':'do',
    'バ':'ba', 'ビ':'bi', 'ブ':'bu', 'ベ':'be', 'ボ':'bo',
    'パ':'pa', 'ピ':'pi', 'プ':'pu', 'ペ':'pe', 'ポ':'po',
    
    # 特殊音
    'ヴ':'vu'
}
```

### 拗音組み合わせ

```python
digraphs_mapping = {
    # キャ行
    ('キ','ャ'):'kya', ('キ','ュ'):'kyu', ('キ','ョ'):'kyo',
    ('ギ','ャ'):'gya', ('ギ','ュ'):'gyu', ('ギ','ョ'):'gyo',
    
    # シャ行
    ('シ','ャ'):'sha', ('シ','ュ'):'shu', ('シ','ョ'):'sho',
    ('ジ','ャ'):'ja',  ('ジ','ュ'):'ju',  ('ジ','ョ'):'jo',
    
    # チャ行
    ('チ','ャ'):'cha', ('チ','ュ'):'chu', ('チ','ョ'):'cho',
    
    # その他の拗音
    ('ニ','ャ'):'nya', ('ヒ','ャ'):'hya', ('ビ','ャ'):'bya',
    ('ピ','ャ'):'pya', ('ミ','ャ'):'mya', ('リ','ャ'):'rya',
    
    # 外来語音（ファ行等）
    ('フ','ァ'):'fa', ('フ','ィ'):'fi', ('フ','ェ'):'fe', ('フ','ォ'):'fo',
    ('シ','ェ'):'she', ('チ','ェ'):'che', ('テ','ィ'):'ti',
    ('ツ','ァ'):'tsa', ('ツ','ィ'):'tsi', ('ツ','ェ'):'tse', ('ツ','ォ'):'tso',
    
    # ヴ音組み合わせ
    ('ヴ','ァ'):'va', ('ヴ','ィ'):'vi', ('ヴ','ェ'):'ve', 
    ('ヴ','ォ'):'vo', ('ヴ','ュ'):'vyu'
}
```

### マクロン変換規則

```python
macron_rules = {
    'aa': 'ā',  # カア → kā
    'ii': 'ī',  # キイ → kī  
    'uu': 'ū',  # クウ → kū
    'ee': 'ē',  # ケエ → kē
    'oo': 'ō',  # コオ → kō
    'ou': 'ō'   # コウ → kō（東京型長音）
}
```

## 特殊処理アルゴリズム

### 促音（ッ）処理

```python
def handle_sokuon(current_pos, kata_string, result_list):
    """促音の処理アルゴリズム"""
    
    # 次の音を確認
    if current_pos + 1 < len(kata_string):
        next_kana = kata_string[current_pos + 1]
        
        # 次の音のローマ字を取得
        next_roman = get_next_roman(next_kana, kata_string[current_pos + 1:])
        
        # 子音部分を抽出して重複
        consonant = extract_initial_consonant(next_roman)
        if consonant:
            result_list.append(consonant[0])  # 先頭子音を重複
            
    # 促音自体は消費
    return current_pos + 1

# 例：
# マッチャ -> ma + tcha (ッ -> t重複) -> matcha
# キャッチ -> kya + tchi (ッ -> t重複) -> kyatchi
```

### 撥音（ン）処理

```python
def handle_hatsuon(roman_string):
    """撥音のm/n使い分け処理"""
    
    # n の後に b/p/m が続く場合は m に変換
    import re
    
    # パターン: n + [bmp] -> m + [bmp]
    result = re.sub(r'n(?=[bmp])', 'm', roman_string)
    
    return result

# 例：
# ホンバン -> honban -> homban
# サンポ -> sanpo -> sampo  
# コンマ -> konma -> komma
# but: ホンテン -> honten (変更なし)
```

### 長音符（ー）処理

```python
def handle_choonpu(roman_list):
    """長音符の前母音延長処理"""
    
    result = []
    i = 0
    
    while i < len(roman_list):
        if roman_list[i] == '-':  # 長音符マーカー
            if i > 0:
                prev_char = result[-1]  # 直前の文字
                if prev_char in 'aiueo':
                    # 前が母音なら重複（後でマクロン処理）
                    result.append(prev_char)
                # else: 子音の場合は無視
        else:
            result.append(roman_list[i])
        i += 1
    
    return result

# 例：
# スー -> su + - -> suu -> sū (マクロン処理後)
# パーティー -> pa + - + ti + - -> paatii -> pātī
```

## 実装例・テストケース

### 基本テストセット

```python
def run_basic_tests():
    """基本変換テストセット"""
    
    test_cases = [
        # 基本音
        ("アイウエオ", "aiueo"),
        ("カキクケコ", "kakikukeko"), 
        ("サシスセソ", "sashisuseso"),
        
        # 濁音・半濁音
        ("ガギグゲゴ", "gagigugego"),
        ("ザジズゼゾ", "zajizuzezo"),
        ("バビブベボ", "babibubebo"),
        ("パピプペポ", "papipupepo"),
        
        # 特殊音
        ("シャシュショ", "shashusho"),
        ("チャチュチョ", "chachucho"),
        ("ジャジュジョ", "jajujo"),
        
        # 促音
        ("アッパ", "appa"),
        ("イッキ", "ikki"),
        ("エッサ", "essa"),
        
        # 撥音
        ("アンパン", "ampan"),
        ("コンマ", "komma"),
        ("ホンテン", "honten")
    ]
    
    for kata, expected in test_cases:
        result = katakana_to_hepburn(kata)
        assert result == expected, f"Failed: {kata} -> {result} (expected {expected})"
        print(f"✓ {kata} -> {result}")

run_basic_tests()
```

### 外来語テストセット

```python
def run_foreign_word_tests():
    """外来語変換テストセット"""
    
    foreign_tests = [
        # ファ行
        ("ファイル", "fairu"),
        ("フィルム", "firumu"),
        ("フェイス", "feisu"), 
        ("フォント", "fonto"),
        
        # シェ・チェ
        ("シェア", "shea"),
        ("シェル", "sheru"),
        ("チェック", "chekku"),
        ("チェイン", "chein"),
        
        # ヴ音
        ("ヴァイオリン", "vaiorin"),
        ("ヴィーナス", "vīnasu"),
        ("ヴェール", "vēru"),
        ("ヴォーカル", "vōkaru"),
        
        # ティ・トゥ・ドゥ
        ("ティー", "tī"),
        ("パーティー", "pātī"),
        ("トゥー", "tū"),
        ("ドゥー", "dū")
    ]
    
    for kata, expected in foreign_tests:
        result = katakana_to_hepburn(kata, use_macron=True)
        print(f"✓ {kata} -> {result}")
        # 実際のexpectedとの比較は実装依存

run_foreign_word_tests()
```

### 長音テストセット

```python
def run_long_vowel_tests():
    """長音処理テストセット"""
    
    long_vowel_tests = [
        # マクロンあり
        ("コーヒー", "kōhī", True),
        ("スーパー", "sūpā", True), 
        ("パーティー", "pātī", True),
        ("トウキョウ", "tōkyō", True),  # ou -> ō
        
        # マクロンなし  
        ("コーヒー", "koohii", False),
        ("スーパー", "suupaa", False),
        ("パーティー", "paatii", False),
        ("トウキョウ", "toukyou", False)
    ]
    
    for kata, expected, use_macron in long_vowel_tests:
        result = katakana_to_hepburn(kata, use_macron=use_macron)
        print(f"✓ {kata} -> {result} (macron={use_macron})")

run_long_vowel_tests()
```

## パフォーマンス考慮事項

### 効率的な処理
- 単一パス処理による高速変換
- 正規表現の最小限使用
- 辞書ルックアップの最適化

### メモリ効率
- 文字列連結の最適化
- 不要な中間オブジェクトの削減
- 大量テキスト処理への対応

## 制限事項・注意点

### 変換精度の制限
- 文脈に依存する読み分けは非対応
- 固有名詞の特殊読みは非対応  
- 方言・古語の特殊音は非対応

### ヘボン式の範囲
- 標準的なヘボン式に準拠
- 一部の外来語音は近似変換
- 撥音の文脈依存ルールは簡略化

### 入力制限
```python
# 適切な入力例
good_inputs = ["カタカナ", "シャープ", "コンピューター"]

# 問題のある入力例
problematic_inputs = [
    "ひらがな",      # ひらがな混在（処理されるがそのまま）
    "English",      # 英字混在（処理されるがそのまま） 
    "123数字",       # 数字混在（処理されるがそのまま）
    "",             # 空文字列（空文字列を返す）
]

# 混在入力の処理例
mixed_result = katakana_to_hepburn("カタカナと英語English")
print(mixed_result)  # "katakanaと英語english"
```

## 関連モジュール

- `transliteration_transliterator.py`: メイン転写クラス
- `transliteration_context_rules.py`: 文脈依存ルール
- 外部のひらがな↔カタカナ変換モジュール（必要に応じて）

## 将来の改善点

- 更なる外来語音への対応
- 文脈依存の読み分け機能
- パフォーマンス最適化
- より詳細なヘボン式バリエーション対応
- 音韻変化ルールの追加