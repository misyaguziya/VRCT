//! Kana as the romaji jaroomaji reads them: Backspace takes a kana shown back to its spelling
//! (kya → ki), keeping the rest of the reading.

/// The romaji jaroomaji reads as `kana`
pub fn romaji(kana: char) -> Option<&'static str> {
    const TABLE: &[(char, &str)] = &[
        ('あ', "a"), ('い', "i"), ('う', "u"), ('え', "e"), ('お', "o"),
        ('か', "ka"), ('き', "ki"), ('く', "ku"), ('け', "ke"), ('こ', "ko"),
        ('さ', "sa"), ('し', "si"), ('す', "su"), ('せ', "se"), ('そ', "so"),
        ('た', "ta"), ('ち', "ti"), ('つ', "tu"), ('て', "te"), ('と', "to"),
        ('な', "na"), ('に', "ni"), ('ぬ', "nu"), ('ね', "ne"), ('の', "no"),
        ('は', "ha"), ('ひ', "hi"), ('ふ', "hu"), ('へ', "he"), ('ほ', "ho"),
        ('ま', "ma"), ('み', "mi"), ('む', "mu"), ('め', "me"), ('も', "mo"),
        ('や', "ya"), ('ゆ', "yu"), ('よ', "yo"),
        ('ら', "ra"), ('り', "ri"), ('る', "ru"), ('れ', "re"), ('ろ', "ro"),
        ('わ', "wa"), ('を', "wo"), ('ん', "nn"), ('ー', "-"),
        ('が', "ga"), ('ぎ', "gi"), ('ぐ', "gu"), ('げ', "ge"), ('ご', "go"),
        ('ざ', "za"), ('じ', "zi"), ('ず', "zu"), ('ぜ', "ze"), ('ぞ', "zo"),
        ('だ', "da"), ('ぢ', "di"), ('づ', "du"), ('で', "de"), ('ど', "do"),
        ('ば', "ba"), ('び', "bi"), ('ぶ', "bu"), ('べ', "be"), ('ぼ', "bo"),
        ('ぱ', "pa"), ('ぴ', "pi"), ('ぷ', "pu"), ('ぺ', "pe"), ('ぽ', "po"),
        ('ぁ', "xa"), ('ぃ', "xi"), ('ぅ', "xu"), ('ぇ', "xe"), ('ぉ', "xo"),
        ('ゃ', "xya"), ('ゅ', "xyu"), ('ょ', "xyo"), ('っ', "xtu"), ('ゎ', "xwa"), ('ゔ', "vu"),
    ];
    TABLE.iter().find(|(k, _)| *k == kana).map(|(_, r)| *r)
}

#[cfg(test)]
mod tests {
    #[test]
    fn small_and_voiced_kana_have_their_romaji() {
        for c in "かがはばぱつっづあぁうぅゔやゃわゎん".chars() {
            assert!(super::romaji(c).is_some(), "{c}");
        }
        assert_eq!(super::romaji('a'), None);
    }
}
