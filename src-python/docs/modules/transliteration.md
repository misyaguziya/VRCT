# models/transliteration — 詳細設計

目的: 日本語テキストの仮名読みを解析し、ひらがな/ローマ字（Hepburn）に変換する。

主要クラス/関数:
- class Transliterator
  - analyze(text: str, use_macron: bool=False) -> List[dict]
    - 入力: テキスト
    - 出力: トークンのリスト。各要素は { orig, kana, hira, hepburn }
  - split_kanji_okurigana(surface, reading_kana): 漢字＋送り仮名を分割して kana を割り当てるロジックを持つ（詳細設計あり）

実装上のポイント:
- SudachiPy を使い形態素解析して読みを得る。
- Katakana を Hiragana に変換し、katakana_to_hepburn モジュールでローマ字化を行う。
- 文脈ルールを `transliteration_context_rules.apply_context_rules` で適用できる設計（ルールエンジン）。

依存: sudachipy
