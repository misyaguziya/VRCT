//! rime.dll with the Japanese (jaroomaji) and Chinese (luna_pinyin) data. Needs
//! VRCT_RIME_DLL (rime.dll) and VRCT_RIME_SHARED (the shared data, as the keyboard sets it up);
//! "SKIPPED" without them.
use std::path::PathBuf;
use vrct_ime::rime::{keys, Rime};

fn typed(session: &vrct_ime::rime::Session, keys: &str) {
    session.clear();
    for k in keys.chars() {
        session.key(k as i32, 0);
    }
}

#[test]
fn japanese_and_chinese_convert() {
    let (Some(dll), Some(shared)) = (std::env::var_os("VRCT_RIME_DLL"), std::env::var_os("VRCT_RIME_SHARED")) else {
        eprintln!("SKIPPED: VRCT_RIME_DLL / VRCT_RIME_SHARED not set");
        return;
    };
    let user = std::env::temp_dir().join(format!("vrct-rime-test-{}", std::process::id()));
    std::fs::create_dir_all(&user).unwrap();
    for (name, contents) in vrct_ime::setup::user_files(&PathBuf::from(&shared)).unwrap() {
        std::fs::write(user.join(name), contents).unwrap();
    }
    let rime = Rime::load(&PathBuf::from(dll)).unwrap();
    assert!(rime.version().starts_with("1.17"), "{}", rime.version());
    rime.start(&PathBuf::from(shared), &user, &user).unwrap();
    assert!(rime.deploy(true));
    let s = rime.session().unwrap();

    assert!(s.select_schema("jaroomaji"));
    s.set_option("ascii_mode", false);
    typed(&s, "kanjihenkan");
    let c = s.context();
    assert_eq!(c.preedit, "かんじへんかん");
    assert_eq!(c.candidates[0], "漢字変換");
    // segment by segment: 今日, then the rest's first candidate
    typed(&s, "kyouhaiitenkidesune");
    let c = s.context();
    let today = c.candidates.iter().position(|t| t == "今日").unwrap();
    assert!(s.select(today));
    let c = s.context();
    assert_eq!(c.preedit, "今日はいいてんきですね");
    assert_eq!(c.selection.0, 2, "{c:?}");
    assert_eq!(c.candidates[0], "はいい天気ですね");
    assert!(s.select(0));
    assert_eq!(s.take_commit().as_deref(), Some("今日はいい天気ですね"));
    // backspace takes the last key back; the consonant being typed shows as it is (not っ)
    typed(&s, "nihongo");
    s.key(keys::BACKSPACE, 0);
    assert_eq!(s.input(), "nihong");
    assert_eq!(s.context().preedit, "にほんg");
    typed(&s, "kitte");
    assert_eq!(s.context().preedit, "きって");
    // n alone spells ん (jaroomaji's own nn too)
    for (keys, shown, first) in [("konnichiha", "こんにちは", "こんにちは"), ("konnnichiha", "こんにちは", "こんにちは"),
                                 ("honnya", "ほんや", "本屋"), ("nn", "ん", "ん")] {
        typed(&s, keys);
        let c = s.context();
        assert_eq!((c.preedit.as_str(), c.candidates[0].as_str()), (shown, first), "{keys}");
    }
    typed(&s, "kanna");
    assert_eq!(s.context().preedit, "かんな");
    assert!(s.context().candidates.iter().any(|c| c == "かんな"));

    assert!(s.select_schema("luna_pinyin"));
    s.set_option("ascii_mode", false);
    typed(&s, "jintiantianqihenhao");
    assert_eq!(s.context().candidates[0], "今天天氣很好");
    s.set_option("zh_hans", true);
    typed(&s, "jintiantianqihenhao");
    assert_eq!(s.context().candidates[0], "今天天气很好");
    drop(s);

    // the keyboard's input over a session
    use vrct_ime::input::{Input, Key, Language};
    let mut i = Input::new(Language::Japanese);
    i.attach(rime.session().unwrap(), false);
    let typed = |i: &mut Input, s: &str| s.chars().for_each(|c| i.key(Key::Char(c)));
    // 変換 shows the first candidate, again the next; 確定 takes the one shown
    typed(&mut i, "kanjihenkan");
    i.key(Key::Space);
    let st = i.state();
    assert!(st.converting && st.highlighted == 0 && st.text.is_empty(), "{st:?}");
    i.key(Key::Space);
    let st = i.state();
    assert_eq!(st.highlighted, 1, "{st:?}");
    i.key(Key::Enter);
    // 感じ: the rest (へんかん) is still being converted, written as its first candidate
    let after = i.state();
    assert!(after.converting && after.composition.unwrap().preedit.starts_with(&st.candidates[1]), "{st:?}");
    assert_eq!(i.take(), format!("{}変換", st.candidates[1]));
    // segment by segment: the rest is being converted
    typed(&mut i, "kyouhaiitenkidesune");
    let today = i.state().candidates.iter().position(|t| t == "今日").unwrap();
    i.select(today);
    let st = i.state();
    // (which candidate comes first here depends on what the session above taught the user dictionary)
    assert!(st.converting && st.composition.as_ref().unwrap().selection.0 == 2, "{st:?}");
    i.key(Key::Enter);
    assert_eq!(i.take(), format!("今日{}", st.candidates[st.highlighted]));
    // 確定 before 変換: the kana; a digit or the keyboard's 、 writes the kana first
    typed(&mut i, "nihongo");
    i.key(Key::Enter);
    typed(&mut i, "kanji2");
    typed(&mut i, "kana");
    i.key(Key::Char('、'));
    assert_eq!(i.state().text, "にほんごかんじ2かな、");
    // switching language writes what was being composed
    typed(&mut i, "ni");
    i.set_language(Language::Chinese);
    typed(&mut i, "zhongwen");
    i.select(0);
    i.set_language(Language::Korean);
    typed(&mut i, "gksrmf");
    assert_eq!(i.take(), "にほんごかんじ2かな、に中文한글");
    // the keyboard's punctuation as Japanese writes it (RIME's own paged with . and converted
    // with ?), but after digits; capitals as typed (jaroomaji's Shift is katakana)
    i.set_language(Language::Japanese);
    for (keys, text) in [("konnichiha.", "こんにちは。"), ("nihongo?", "にほんご？"), ("1.5", "1.5"), ("[a]", "「あ」"), ("VRCTdesu", "VRCTです")] {
        typed(&mut i, keys);
        assert_eq!(i.take(), text, "{keys}");
    }
    // 半角/全角: what was being composed is written, then the keys as they are; again: kana
    typed(&mut i, "ni");
    i.key(Key::HalfWidth);
    typed(&mut i, "ok,");
    i.key(Key::HalfWidth);
    typed(&mut i, "ne");
    assert_eq!(i.take(), "にok,ね");
    // Ctrl+Z while composing drops only the word being composed; Ctrl+A writes it first
    typed(&mut i, "nihon");
    i.key(Key::Undo);
    assert!(i.state().composition.is_none() && i.state().text.is_empty(), "{:?}", i.state());
    typed(&mut i, "kana");
    i.key(Key::SelectAll);
    assert_eq!(i.selected_text().as_deref(), Some("かな"));
    typed(&mut i, "ne");
    assert_eq!(i.take(), "ね");
    i.set_language(Language::Chinese);
    typed(&mut i, "nihao,");
    assert_eq!(i.take(), "你好，");
    // Zhuyin on the Dachen layout: ㄋㄧˇ ㄏㄠˇ (s u 3, c l 3; shown with a space between the syllables); its comma with Shift
    i.set_language(Language::Zhuyin);
    typed(&mut i, "su3cl3");
    let st = i.state();
    assert_eq!((st.composition.as_ref().unwrap().preedit.as_str(), st.candidates[0].as_str()), ("ㄋㄧˇ ㄏㄠˇ", "你好"), "{st:?}");
    i.select(0);
    typed(&mut i, "<");
    assert_eq!(i.take(), "你好，");
    // Cangjie: 明 is 日月 (a b), shown as its radicals; Quick: 你 is 人火 (first and last of 人弓火)
    i.set_language(Language::Cangjie);
    typed(&mut i, "ab");
    let st = i.state();
    assert_eq!((st.composition.as_ref().unwrap().preedit.as_str(), st.candidates[0].as_str()), ("日月", "明"), "{st:?}");
    i.key(Key::Space);
    assert_eq!(i.take(), "明");
    i.set_language(Language::Quick);
    typed(&mut i, "of");
    assert!(i.state().candidates.iter().any(|c| c == "你"), "{:?}", i.state());
    let _ = std::fs::remove_dir_all(&user);
}
