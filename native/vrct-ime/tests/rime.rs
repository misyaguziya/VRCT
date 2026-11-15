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
    // as under a Japanese Windows user name, the logs relative to it as the keyboard has them (テ in
    // an absolute log_dir aborts librime)
    let root = std::env::temp_dir().join(format!("vrct-rime-test-テスト ユーザー-{}", std::process::id()));
    let user = root.join("user");
    std::fs::create_dir_all(&user).unwrap();
    for (name, contents) in vrct_ime::setup::user_files(&PathBuf::from(&shared)).unwrap() {
        std::fs::write(user.join(name), contents).unwrap();
    }
    let rime = Rime::load(&PathBuf::from(dll)).unwrap();
    assert!(rime.version().starts_with("1.17"), "{}", rime.version());
    std::env::set_current_dir(&root).unwrap();
    rime.start(&PathBuf::from(shared), &user, std::path::Path::new("logs")).unwrap();
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
    // The schema accepts explicit small-tsu spellings; ordinary typing expands them in Input.
    for raw in ["fht", "kht", "f", "k", "fh"] {
        typed(&s, raw);
        let c = s.context();
        assert!(c.candidates.iter().all(|candidate| !candidate.contains(['っ', 'ッ', 'ｯ'])), "{raw}: {c:?}");
    }
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
    for (raw, wide) in [("123", "１２３"), ("1.5", "１．５"), ("1,000", "１，０００")] {
        typed(&mut i, raw);
        assert_eq!(i.state().candidates, [raw, wide]);
        i.key(Key::Enter);
        assert_eq!(i.take(), raw);
        typed(&mut i, raw);
        i.select(1);
        assert_eq!(i.take(), wide);
        for finish in [Key::Enter, Key::Tab, Key::HalfWidth] {
            typed(&mut i, raw);
            i.key(Key::Space);
            i.key(Key::Space);
            assert_eq!(i.state().highlighted, 1);
            i.key(Key::PageDown);
            i.key(Key::PageUp);
            assert_eq!(i.state().highlighted, 1);
            i.key(finish);
            assert_eq!(i.take(), wide);
            if finish == Key::HalfWidth { i.key(Key::HalfWidth); }
        }
    }
    typed(&mut i, "123");
    i.key(Key::Space);
    i.key(Key::Space);
    i.key(Key::Left);
    i.key(Key::Right);
    assert!(!i.state().converting);
    assert_eq!(i.state().highlighted, 0);
    i.key(Key::Char('4'));
    assert_eq!(i.state().candidates, ["1234", "１２３４"]);
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().preedit, "123");
    i.key(Key::Space);
    i.key(Key::Space);
    i.set_language(Language::English);
    assert_eq!(i.take(), "１２３");
    i.set_language(Language::Japanese);
    typed(&mut i, "123");
    i.key(Key::Space);
    i.key(Key::Space);
    typed(&mut i, "ka");
    assert!(!i.state().converting);
    assert_eq!(i.state().composition.unwrap().preedit, "123か");
    assert_eq!(i.take(), "123か");
    typed(&mut i, "１２.５");
    assert_eq!(i.state().candidates, ["１２.５", "12.5", "１２．５"]);
    i.select(2);
    assert_eq!(i.take(), "１２．５");
    for key in "1234567890^¥!\"#$%&'()=~|".chars() {
        i.key(Key::Char(key));
        let state = i.state();
        assert!(state.text.is_empty(), "top row commit {key}: {state:?}");
        assert!(state.candidates.len() > 1, "top row alternatives {key}: {state:?}");
        assert_eq!(state.composition.unwrap().preedit, match key { '~' => "〜".to_string(), '!' => "！".to_string(), _ => key.to_string() });
        i.key(Key::Backspace);
        assert!(i.state().composition.is_none(), "delete top row {key}");
    }
    for (raw, expected) in [("k123", "k123"), ("1.5", "1.5"), ("1,000", "1,000"), ("ko-hi-", "こーひー")] {
        typed(&mut i, raw);
        assert!(i.state().text.is_empty());
        assert_eq!(i.state().composition.unwrap().preedit, expected);
        assert_eq!(i.take(), expected);
    }
    // Punctuation is editable RIME input, not a boundary that commits unfinished romaji.
    for (raw, expected) in [("k.", "k。"), ("ka,", "か、"), ("ka[", "か「"), ("k”", "k”"), ("ka。ka", "か。か"),
                            ("ka。kitte", "か。きって"), ("ka。matcha", "か。まっちゃ")] {
        typed(&mut i, raw);
        let state = i.state();
        assert!(state.text.is_empty(), "premature punctuation commit: {raw}: {state:?}");
        assert_eq!(state.composition.unwrap().preedit, expected);
        i.key(Key::Enter);
        assert_eq!(i.take(), expected);
    }
    typed(&mut i, "ka。kya");
    for expected in ["か。き", "か。", "か", ""] {
        i.key(Key::Backspace);
        assert_eq!(i.state().composition.map(|c| c.preedit).unwrap_or_default(), expected);
    }
    typed(&mut i, "k。");
    i.key(Key::HalfWidth);
    assert_eq!(i.state().text, "k。");
    i.clear();
    i.key(Key::HalfWidth);
    // Unrecognized consonants remain literal without blocking later valid syllables.
    // The whole reading stays editable; no prefix is committed behind the user's back.
    for (raw, expected) in [("fi", "ふぃ"), ("fiiii", "ふぃいいい"), ("kjfiiii", "kjふぃいいい"),
                            ("kfi", "kふぃ"), ("jfi", "jふぃ"), ("kja", "kじゃ"), ("kjka", "kjか")] {
        typed(&mut i, raw);
        let state = i.state();
        assert!(state.text.is_empty(), "premature commit {raw}: {state:?}");
        assert_eq!(state.composition.unwrap().preedit, expected, "{raw}");
        i.key(Key::Enter);
        assert_eq!(i.take(), expected, "commit {raw}");
    }
    typed(&mut i, "kjfiiii");
    for expected in ["kjふぃいい", "kjふぃい", "kjふぃ", "kjふ", "kj", "k", ""] {
        i.key(Key::Backspace);
        assert_eq!(i.state().composition.map(|c| c.preedit).unwrap_or_default(), expected);
    }
    typed(&mut i, "kjfi");
    i.key(Key::Undo);
    assert!(i.state().composition.is_none() && i.state().text.is_empty());
    typed(&mut i, "kjfi");
    let candidate = i.state().candidates[0].clone();
    assert!(candidate.starts_with("kj") && candidate.contains('ふ'), "{candidate}");
    i.select(0);
    assert_eq!(i.take(), candidate);
    typed(&mut i, "kyouk");
    let today = i.state().candidates.iter().position(|c| c == "今日").unwrap();
    i.select(today);
    typed(&mut i, "jfi");
    let c = i.state().composition.unwrap();
    assert_eq!(c.preedit, "今日kjふぃ");
    assert_eq!(c.selection.0, 2);
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().preedit, "今日kjふ");
    i.clear();
    typed(&mut i, "kaka");
    i.key(Key::Left);
    let c = i.state().composition.unwrap();
    let right: String = c.preedit.chars().skip(c.cursor).collect();
    typed(&mut i, "kjfi");
    let c = i.state().composition.unwrap();
    assert_eq!(c.preedit, format!("かkjふぃ{right}"));
    assert_eq!(c.cursor, 5);
    i.key(Key::Backspace);
    let c = i.state().composition.unwrap();
    assert_eq!(c.preedit, format!("かkjふ{right}"));
    assert_eq!(c.cursor, 4);
    i.finish_composition();
    assert_eq!(i.take(), "かkjふか");
    // Rapid alternating keys must not expose the internal xtu spelling.
    for raw in ["hjhjhjhjhj", "jhjhjhjhjh", "hhjjhhjj", "hjjh", "jhhj", "fhtt", "khkk"] {
        i.clear();
        for c in raw.chars() {
            i.key(Key::Char(c));
            let state = i.state();
            let shown = state.text + &state.composition.map(|c| c.preedit).unwrap_or_default();
            assert!(!shown.contains('x'), "{raw} after {c}: {shown}");
        }
        let state = i.state();
        let shown = state.text + &state.composition.map(|c| c.preedit).unwrap_or_default();
        i.key(Key::Enter);
        assert_eq!(i.take(), shown, "commit {raw}");
        typed(&mut i, raw);
        for _ in 0..raw.len() {
            i.key(Key::Backspace);
            let state = i.state();
            let shown = state.text + &state.composition.map(|c| c.preedit).unwrap_or_default();
            assert!(!shown.contains('x'), "backspace {raw}: {shown}");
        }
        assert!(i.state().composition.is_none(), "delete {raw}");
        assert_eq!(i.state().text, "", "delete {raw}");
    }
    i.clear();
    for (raw, shown) in [("fht", "fht"), ("kht", "kht"), ("kk", "っk"), ("gakkou", "がっこう"),
                         ("xtsu", "っ"), ("xtu", "っ"), ("kya", "きゃ"), ("kitte", "きって"),
                         ("matcha", "まっちゃ"), ("witchi", "うぃっち"), ("tc", "tc"), ("kkk", "っっk"), ("nn", "ん"), ("VRCT", "VRCT")] {
        typed(&mut i, raw);
        assert_eq!(i.state().text + &i.state().composition.map(|c| c.preedit).unwrap_or_default(), shown, "{raw}");
        i.key(Key::Enter);
        assert_eq!(i.take(), shown, "commit {raw}");
    }
    for (raw, candidate) in [("kitte", "切手"), ("gakkou", "学校"), ("matcha", "抹茶")] {
        typed(&mut i, raw);
        let st = i.state();
        let index = st.candidates.iter().position(|c| c == candidate).expect(raw);
        i.select(index);
        assert_eq!(i.take(), candidate);
    }
    for raw in ["f", "k", "h", "t", "fht", "kht", "kafht", "nihong"] {
        i.clear();
        typed(&mut i, raw);
        let candidates = i.state().candidates;
        let no_candidates = candidates.is_empty();
        let shown = i.state().composition.unwrap().preedit;
        assert!(candidates.iter().all(|c| !c.contains(['っ', 'ッ', 'ｯ'])), "{raw}: {candidates:?}");
        for index in 0..candidates.len() {
            i.clear();
            typed(&mut i, raw);
            i.select(index);
            assert!(!i.take().contains(['っ', 'ッ', 'ｯ']), "selected {raw}/{index}");
        }
        i.clear();
        typed(&mut i, raw);
        i.key(Key::Space);
        i.key(Key::Enter);
        let committed = i.take();
        assert!(!committed.contains(['っ', 'ッ', 'ｯ']), "converted {raw}");
        if no_candidates {
            assert_eq!(committed, shown, "unconverted {raw}");
        }
        if matches!(raw, "f" | "k" | "h" | "t" | "fht" | "kht") {
            assert_eq!(committed, raw, "literal {raw}");
        }
    }
    for (key, expected) in [('k', "k"), ('k', "っk"), ('a', "っか")] {
        i.key(Key::Char(key));
        assert_eq!(i.state().composition.unwrap().preedit, expected);
    }
    i.clear();
    typed(&mut i, "kk");
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().preedit, "っ");
    i.key(Key::Backspace);
    assert!(i.state().composition.is_none());
    typed(&mut i, "kaka");
    i.key(Key::Left);
    typed(&mut i, "kka");
    assert_eq!(i.take(), "かっかか");
    typed(&mut i, "kyouk");
    let today = i.state().candidates.iter().position(|c| c == "今日").unwrap();
    i.select(today);
    typed(&mut i, "itte");
    assert_eq!(i.state().composition.unwrap().preedit, "今日きって");
    i.clear();
    // A rejected expansion must preserve selected text and text after the caret.
    typed(&mut i, "kyouh");
    let today = i.state().candidates.iter().position(|c| c == "今日").unwrap();
    i.select(today);
    typed(&mut i, "hjj");
    let c = i.state().composition.unwrap();
    assert!(c.preedit.starts_with("今日") && !c.preedit.contains('x'), "{c:?}");
    assert_eq!(c.selection.0, 2);
    i.clear();
    typed(&mut i, "kaka");
    i.key(Key::Left);
    let c = i.state().composition.unwrap();
    let suffix: String = c.preedit.chars().skip(c.cursor).collect();
    typed(&mut i, "hhjj");
    let c = i.state().composition.unwrap();
    assert!(c.preedit.starts_with('か') && !c.preedit.contains('x'), "{c:?}");
    assert_eq!(c.preedit.chars().skip(c.cursor).collect::<String>(), suffix);
    i.clear();
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
    // 確定 before 変換: the kana. Digits and punctuation stay in composition.
    typed(&mut i, "nihongo");
    i.key(Key::Enter);
    typed(&mut i, "kanji2");
    typed(&mut i, "kana");
    i.key(Key::Char('、'));
    assert_eq!(i.state().text, "にほんご");
    assert_eq!(i.state().composition.unwrap().preedit, "かんじ2かな、");
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
    for (raw, expected) in [("kya", "き"), ("kitte", "きっ"), ("kann", "か"),
                             ("kak", "か"), ("ka", ""), ("xtu", ""), ("k", ""), ("fht", "fh")] {
        typed(&mut i, raw);
        i.key(Key::Backspace);
        assert_eq!(i.state().composition.map(|c| c.preedit).unwrap_or_default(), expected, "{raw}");
        i.clear();
    }
    typed(&mut i, "kanji");
    i.key(Key::Space);
    i.key(Key::Backspace);
    assert!(!i.state().converting);
    assert_eq!(i.state().composition.unwrap().preedit, "かんじ");
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().preedit, "かん");
    i.clear();
    typed(&mut i, "kyouhaiitenkidesune");
    let today = i.state().candidates.iter().position(|t| t == "今日").unwrap();
    i.select(today);
    i.key(Key::Backspace);
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().preedit, "今日はいいてんきです");
    for expected in ["今日はいいてんきで", "今日はいいてんき", "今日はいいてん", "今日はいいて", "今日はいい", "今日はい", "今日は", "今日", "きょう", "きょ", "き"] {
        i.key(Key::Backspace);
        assert_eq!(i.state().composition.unwrap().preedit, expected);
    }
    i.clear();
    typed(&mut i, "kakiku");
    assert_eq!(i.state().composition.unwrap().cursor, 3);
    i.key(Key::Left);
    assert_eq!(i.state().composition.unwrap().cursor, 2);
    i.key(Key::Left);
    assert_eq!(i.state().composition.unwrap().cursor, 1);
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().cursor, 0);
    assert_eq!(i.state().composition.unwrap().preedit, "きく");
    typed(&mut i, "sa");
    assert_eq!(i.take(), "さきく");
    typed(&mut i, "kyaka");
    i.key(Key::Left);
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().preedit, "きka");
    i.finish_composition();
    assert_eq!(i.state().text, "きか");
    i.clear();
    typed(&mut i, "kyouhaii");
    let kana = i.state().candidates.iter().position(|t| t == "きょう").unwrap();
    i.select(kana);
    i.key(Key::Backspace);
    for expected in ["きょうはい", "きょうは", "きょう"] {
        i.key(Key::Backspace);
        assert_eq!(i.state().composition.unwrap().preedit, expected);
    }
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().preedit, "きょう");
    i.key(Key::Backspace);
    assert_eq!(i.state().composition.unwrap().preedit, "きょ");
    i.clear();
    for raw in ["ka", "kak"] {
        typed(&mut i, raw);
        let shown = i.state().composition.unwrap().preedit;
        i.finish_composition();
        assert_eq!(i.state().text, shown);
        assert!(i.state().composition.is_none());
        i.clear();
    }
    // Tab takes the candidate highlighted; not composing, it does nothing
    typed(&mut i, "kanji");
    i.key(Key::Space);
    i.key(Key::Space);
    let candidate = i.state().candidates[i.state().highlighted].clone();
    i.key(Key::Tab);
    assert_eq!(i.take(), candidate);
    i.key(Key::Tab);
    assert_eq!(i.state().text, "");
    typed(&mut i, "kanji");
    i.key(Key::Space);
    let candidate = i.state().candidates[i.state().highlighted].clone();
    i.finish_composition();
    assert_eq!(i.state().text, candidate);
    assert!(i.state().composition.is_none());
    i.key(Key::Undo);
    assert_eq!(i.state().text, "");
    i.clear();
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
