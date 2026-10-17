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
    std::fs::write(user.join("default.custom.yaml"),
                   "patch:\n  schema_list:\n    - schema: jaroomaji\n    - schema: luna_pinyin\n").unwrap();
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
    // backspace takes the last key back (jaroomaji shows a lone consonant as っ: the keyboard
    // shows the keys instead)
    typed(&s, "nihongo");
    s.key(keys::BACKSPACE, 0);
    assert_eq!(s.input(), "nihong");
    assert_eq!(s.context().preedit, "にほんっ");

    assert!(s.select_schema("luna_pinyin"));
    s.set_option("ascii_mode", false);
    typed(&s, "jintiantianqihenhao");
    assert_eq!(s.context().candidates[0], "今天天氣很好");
    s.set_option("zh_hans", true);
    typed(&s, "jintiantianqihenhao");
    assert_eq!(s.context().candidates[0], "今天天气很好");
    drop(s);
    let _ = std::fs::remove_dir_all(&user);
}
