//! Literal punctuation shared by the Japanese schema and editor. The selected glyph is first;
//! related forms remain available through normal candidate selection.
pub(crate) const GROUPS: &[&str] = &[
    "。．.", "、，,", "！!", "？?", "「『【〔［｛[{", "」』】〕］｝]}",
    "（(", "）)", "〈《<", "〉》>", "“”\"", "‘’'", "・…／/", "＼￥¥\\", "〜～~", "ー−－-",
    "0０", "1１", "2２", "3３", "4４", "5５", "6６", "7７", "8８", "9９",
    "：:", "；;", "＿_", "＝=", "＋+", "＊*", "＆&", "％%", "＃#", "＄$", "＠@", "＾^", "｀`", "｜|", "　",
];

pub(crate) fn supported(c: char) -> bool {
    GROUPS.iter().any(|group| group.contains(c))
}

pub(crate) fn entries() -> impl Iterator<Item = (char, String, &'static str)> {
    GROUPS.iter().flat_map(|&group| group.chars().map(move |c| (c, format!("Q{}Z", c as u32), group)))
}

pub(crate) fn spelling(c: char) -> Option<String> {
    entries().find(|(glyph, _, _)| *glyph == c).map(|(_, code, _)| code)
}
