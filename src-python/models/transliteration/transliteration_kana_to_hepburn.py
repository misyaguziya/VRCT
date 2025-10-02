# katakana_to_hepburn.py
# カタカナ -> ヘボン式ローマ字（パッケージ不要）

def katakana_to_hepburn(kata: str, use_macron: bool = True) -> str:
    """
    カタカナ文字列をヘボン式ローマ字に変換する。
    use_macron=True のとき ā ī ū ē ō で長音を表現（マクロン）。
    use_macron=False のときは単純に連続母音を残す（例: ou, oo）。
    """
    # 基本音の対応（主要なカタカナ）
    base = {
        'ア':'a','イ':'i','ウ':'u','エ':'e','オ':'o',
        'カ':'ka','キ':'ki','ク':'ku','ケ':'ke','コ':'ko',
        'サ':'sa','シ':'shi','ス':'su','セ':'se','ソ':'so',
        'タ':'ta','チ':'chi','ツ':'tsu','テ':'te','ト':'to',
        'ナ':'na','ニ':'ni','ヌ':'nu','ネ':'ne','ノ':'no',
        'ハ':'ha','ヒ':'hi','フ':'fu','ヘ':'he','ホ':'ho',
        'マ':'ma','ミ':'mi','ム':'mu','メ':'me','モ':'mo',
        'ヤ':'ya','ユ':'yu','ヨ':'yo',
        'ラ':'ra','リ':'ri','ル':'ru','レ':'re','ロ':'ro',
        'ワ':'wa','ヲ':'wo','ン':'n',
        'ガ':'ga','ギ':'gi','グ':'gu','ゲ':'ge','ゴ':'go',
        'ザ':'za','ジ':'ji','ズ':'zu','ゼ':'ze','ゾ':'zo',
        'ダ':'da','ヂ':'ji','ヅ':'zu','デ':'de','ド':'do',
        'バ':'ba','ビ':'bi','ブ':'bu','ベ':'be','ボ':'bo',
        'パ':'pa','ピ':'pi','プ':'pu','ペ':'pe','ポ':'po',
        # 小書き（単独で使われることは少ないがマップしておく）
        'ァ':'a','ィ':'i','ゥ':'u','ェ':'e','ォ':'o',
        'ャ':'ya','ュ':'yu','ョ':'yo','ッ':'xtsu','ー':'-',
        'ヴ':'vu','シェ':'she'  # 特殊は下で組合せで処理
    }

    # 拡張：子音 + 小ャユョ の組合せ（主要なもの）
    digraphs = {
        ('キ','ャ'):'kya', ('キ','ュ'):'kyu', ('キ','ョ'):'kyo',
        ('ギ','ャ'):'gya', ('ギ','ュ'):'gyu', ('ギ','ョ'):'gyo',
        ('シ','ャ'):'sha', ('シ','ュ'):'shu', ('シ','ョ'):'sho',
        ('ジ','ャ'):'ja',  ('ジ','ュ'):'ju',  ('ジ','ョ'):'jo',
        ('チ','ャ'):'cha', ('チ','ュ'):'chu', ('チ','ョ'):'cho',
        ('ニ','ャ'):'nya', ('ニ','ュ'):'nyu', ('ニ','ョ'):'nyo',
        ('ヒ','ャ'):'hya', ('ヒ','ュ'):'hyu', ('ヒ','ョ'):'hyo',
        ('ビ','ャ'):'bya', ('ビ','ュ'):'byu', ('ビ','ョ'):'byo',
        ('ピ','ャ'):'pya', ('ピ','ュ'):'pyu', ('ピ','ョ'):'pyo',
        ('ミ','ャ'):'mya', ('ミ','ュ'):'myu', ('ミ','ョ'):'myo',
        ('リ','ャ'):'rya', ('リ','ュ'):'ryu', ('リ','ョ'):'ryo',
        # 外来音対応（ファ/フィ/チェ 等）
        ('フ','ャ'):'fya', ('フ','ュ'):'fyu', ('フ','ョ'):'fyo',
        ('ト','ゥ'):'tu', ('ド','ゥ'):'du',
        # F-sounds (ファ フィ フェ フォ)
        ('フ','ァ'):'fa', ('フ','ィ'):'fi', ('フ','ェ'):'fe', ('フ','ォ'):'fo',
        # シェ チェ ティ etc.
        ('シ','ェ'):'she', ('チ','ェ'):'che',
        ('テ','ィ'):'ti', ('ト','ゥ'):'tu', ('ド','ゥ'):'du',
        ('ウ','ァ'):'wa', ('ウ','ィ'):'wi', ('ウ','ェ'):'we', ('ウ','ォ'):'wo',
        # その他外来語によくある組合せ
        ('ス','ィ'):'si', ('ズ','ィ'):'zi', ('ツ','ァ'):'tsa', ('ツ','ィ'):'tsi', ('ツ','ェ'):'tse', ('ツ','ォ'):'tso',
        ('キ','ェ'):'kye', ('ギ','ェ'):'gye',
        ('ヴ','ァ'):'va', ('ヴ','ィ'):'vi', ('ヴ','ェ'):'ve', ('ヴ','ォ'):'vo', ('ヴ','ュ'):'vyu'
    }

    # 小文字一覧（ゃゅょぁぃぅぇぉ など）
    small_kana = set(['ャ','ュ','ョ','ァ','ィ','ゥ','ェ','ォ','ヮ','ヵ','ヶ','ッ','ャ','ュ','ョ'])

    # マクロン変換マップ（連続母音 -> マクロン）
    macron_map = {
        'aa':'ā','ii':'ī','uu':'ū','ee':'ē','oo':'ō',
        # ou -> ō という扱いを多くのヘボン式はする（特に日本語由来の長音）
        'ou':'ō'
    }

    # Helper: 次のローマ字の先頭子音を取り出す（促音処理用）
    def initial_consonant(rom: str) -> str:
        # romはローマ字（例 'shi','chi','ta'）
        # 子音は最初の母音直前までと考える（母音: a,i,u,e,o）
        for i,ch in enumerate(rom):
            if ch in 'aeiou':
                return rom[:i]
        return rom  # 母音がないなら全部

    # 変換メイン
    res = []
    i = 0
    kata = kata.strip()
    length = len(kata)

    while i < length:
        ch = kata[i]

        # 促音（ッ）：次の音の初めの子音を重ねる
        if ch == 'ッ':
            # lookahead
            if i+1 < length:
                # 先の1文字 or 合字を取り得る（小書きが続く可能性）
                # まず合字優先で調べる
                next_pair = None
                if i+2 < length and (kata[i+1], kata[i+2]) in digraphs:
                    next_pair = digraphs[(kata[i+1], kata[i+2])]
                elif kata[i+1] in base:
                    next_pair = base.get(kata[i+1])

                if next_pair:
                    cons = initial_consonant(next_pair)
                    if cons == '':
                        # もし母音始まりなら促音は無視（稀）
                        pass
                    else:
                        # Hepburnでは "ch" の場合 "cch"（matcha）等の扱いになるように
                        # cons の先頭1文字を倍にするより、cons全体の先頭文字を重ねるのが一般的（例: 'shi' -> 'ssh' ? いい例は少ない）
                        # 実務上は先頭子音の最初の文字を重複する：
                        res.append(cons[0])
                # advance only the 促音 itself here; next loop handles next kana
            i += 1
            continue

        # 長音符（ー）：前の母音を伸ばす（マクロン処理は後でまとめて）
        if ch == 'ー':
            # append marker '-' to indicate prolong; we'll post-process
            res.append('-')
            i += 1
            continue

        # 合字（子 + 小ャュョ等）
        if i+1 < length and (ch, kata[i+1]) in digraphs:
            res.append(digraphs[(ch, kata[i+1])])
            i += 2
            continue

        # 小書きが前に独立して出てきた場合（通常は合字で処理されるが念のため）
        if ch in small_kana and ch != 'ッ':
            # 小書きを単独で英字に変換（例: 'ァ' -> 'a'）
            res.append(base.get(ch, ''))
            i += 1
            continue

        # 普通のカタカナ
        if ch in base:
            res.append(base[ch])
            i += 1
            continue

        # 英数字や記号・ひらがななどはそのまま（変換対象外）
        res.append(ch)
        i += 1

    # ここまでで res はローマ字パーツのリスト（長音は '-' でマーク）
    raw = ''.join(res)

    # 撥音（ン）処理: n の前が b/p/m の場合 m にする
    # ただし既に 'n' のまま次が母音や y の時は通常 n' を入れるべきだが簡易処理として n のまま保持。
    # 我々は 'n' の後に b/p/m が来たら 'm' に置換
    import re
    raw = re.sub(r'n(?=[bmp])', 'm', raw)

    # 長音処理（'-' マークを見て前の母音を伸ばす）
    # raw 中の '-' を削って該当の母音を伸ばす
    while '-' in raw:
        idx = raw.find('-')
        if idx == 0:
            # 先頭に長音符が来るのはおかしいので削除
            raw = raw[:idx] + raw[idx+1:]
            continue
        # 前の文字が母音ならそれを重ねる
        prev = raw[idx-1]
        if prev in 'aiueo':
            # 直前に既に vowel がある場合、後でマクロン処理に任せて母音を2つにする
            raw = raw[:idx] + prev + raw[idx+1:]
        else:
            # 直前が子音なら何もして取り除く
            raw = raw[:idx] + raw[idx+1:]

    # 小さな例外対応： 'ti' 等の表記は 'chi' と扱いたいが上述マップでカバー済み
    # macron の適用（長音の正規化）
    if use_macron:
        # まず 'ou' を ō に（ただし語による例外はあるが、一般的ヘボンに合わせる）
        # その前に 'oo' を 'ō' に（稀）
        for pair, mac in macron_map.items():
            raw = raw.replace(pair, mac)
    # else: leave as is (ou/oo/aa...)

    # 仕上げ：小文字統一（ヘボンは小文字）
    raw = raw.lower()

    # 最後に、n の後に母音または y が来る場合は「んあ->n'a」的扱いが必要だが
    # シンプル実装では n の後に母音や y が来るときは n' を入れる（明瞭化）
    # ただし多くの実例では省略されることも多いのでコメントアウトしておく
    # raw = re.sub(r"n(?=[aiueoy])", "n'", raw)

    return raw


# --- テスト例 ---
if __name__ == "__main__":
    tests = [
        "カタカナ",
        "コンピューター",
        "キャッチ",
        "マッチャ",
        "シェア",
        "ジェット",
        "ヴァイオリン",
        "ホテル",
        "スーパー",
        "ギュウニュウ",
        "パーティー",
        "トウキョウ",    # 東京（トウキョウ -> tōkyō）
        "オーケー",
        "ファイル",
        "ニューヨーク",
        "ラーメン",
        "パン",
        "チョコレート",
        "シイ"
    ]

    for s in tests:
        print(s, "->", katakana_to_hepburn(s, use_macron=False))