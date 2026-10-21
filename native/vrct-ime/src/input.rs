//! What the keyboard holds while typing: the text written so far and the word being composed,
//! by language. English goes in as typed, Korean through the Hangul composer, Japanese and
//! Chinese through a RIME session (when the dictionaries are ready).
use crate::hangul::{jamo_of_key, Composer};
use crate::rime::{keys, Session};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Language {
    Japanese,
    English,
    Korean,
    Chinese,
}

impl Language {
    pub fn from_code(code: &str) -> Option<Language> {
        Some(match code {
            "ja" => Language::Japanese,
            "en" => Language::English,
            "ko" => Language::Korean,
            "zh" => Language::Chinese,
            _ => return None,
        })
    }

    pub fn code(self) -> &'static str {
        match self {
            Language::Japanese => "ja",
            Language::English => "en",
            Language::Korean => "ko",
            Language::Chinese => "zh",
        }
    }

    /// The RIME schema it types with (None: no dictionary needed)
    pub fn schema(self) -> Option<&'static str> {
        match self {
            Language::Japanese => Some("jaroomaji"),
            Language::Chinese => Some("luna_pinyin"),
            _ => None,
        }
    }
}

/// A key of the keyboard
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Key {
    /// a letter, digit or symbol; uppercase when typed with Shift
    Char(char),
    Backspace,
    Space,
    Enter,
    Left,
    Right,
    PageUp,
    PageDown,
}

/// The word being composed (Japanese, Chinese): as shown, the segment being chosen and the caret
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Composition {
    pub preedit: String,
    pub selection: (usize, usize),
    pub cursor: usize,
}

/// Everything the keyboard shows
#[derive(Clone, Debug, Default, PartialEq)]
pub struct State {
    /// written so far, up to the cursor (the composition not included: it is at the cursor)
    pub text: String,
    /// written after the cursor
    pub after: String,
    pub composition: Option<Composition>,
    pub candidates: Vec<String>,
    /// the candidate 確定 takes (index on the page)
    pub highlighted: usize,
    /// Japanese: 変換 was pressed, the segment shows as its highlighted candidate
    pub converting: bool,
    pub page: usize,
    pub last_page: bool,
    /// Korean: the syllable being made and its jamo
    pub syllable: Option<(String, Vec<char>)>,
    /// characters of the text (both sides of the cursor) and what is being composed (VRChat's chat box takes 144)
    pub length: usize,
}

pub struct Input<'r> {
    /// written up to the cursor: what is typed goes here (at the cursor)
    text: String,
    /// written after the cursor (◀ ▶ move characters between the two)
    after: String,
    language: Language,
    rime: Option<Session<'r>>,
    hangul: Composer,
    converting: bool,
}

impl<'r> Input<'r> {
    pub fn new(language: Language) -> Self {
        Self { text: String::new(), after: String::new(), language, rime: None, hangul: Composer::new(), converting: false }
    }

    /// The RIME session, once the dictionaries are ready (Japanese and Chinese type from then on)
    pub fn attach(&mut self, session: Session<'r>, simplified: bool) {
        self.rime = Some(session);
        self.set_simplified(simplified);
        self.select_schema();
    }

    pub fn language(&self) -> Language {
        self.language
    }

    /// The language can be typed now (Japanese and Chinese need the dictionaries)
    pub fn available(&self, language: Language) -> bool {
        language.schema().is_none() || self.rime.is_some()
    }

    fn select_schema(&self) {
        if let (Some(s), Some(schema)) = (&self.rime, self.language.schema()) {
            s.select_schema(schema);
            // jaroomaji starts in its ASCII mode
            s.set_option("ascii_mode", false);
        }
    }

    /// Switches language; what was being composed is written first
    pub fn set_language(&mut self, language: Language) {
        if language != self.language {
            self.flush();
            self.language = language;
            self.select_schema();
        }
    }

    pub fn set_simplified(&self, simplified: bool) {
        if let Some(s) = &self.rime {
            // luna_pinyin's switch: Simplified through OpenCC (only the Chinese schema has it)
            s.set_option("zh_hans", simplified);
        }
    }

    fn session(&self) -> Option<&Session<'r>> {
        self.rime.as_ref().filter(|_| self.language.schema().is_some())
    }

    /// A word is being composed (Japanese, Chinese): Enter commits it rather than sending
    pub fn composing(&self) -> bool {
        self.session().is_some_and(|s| !s.input().is_empty())
    }

    /// What RIME committed goes into the text
    fn collect(&mut self) {
        if let Some(text) = self.session().and_then(|s| s.take_commit()) {
            self.text += &text;
        }
        self.converting &= self.composing();
    }

    /// The composition as shown (RIME's) or the Korean syllables, into the text: Japanese before
    /// 変換 is its kana (RIME would write the first candidate)
    fn flush(&mut self) {
        let kana = self.language == Language::Japanese && !self.converting;
        if let Some(s) = self.session() {
            if !s.input().is_empty() {
                if kana {
                    s.key(keys::RETURN, 0);
                } else {
                    s.commit_composition();
                }
            }
        }
        self.collect();
        self.text += &self.hangul.take();
    }

    pub fn key(&mut self, key: Key) {
        match self.language {
            Language::English => match key {
                Key::Char(c) => self.text.push(c),
                Key::Space => self.text.push(' '),
                Key::Backspace => {
                    self.text.pop();
                }
                Key::Left | Key::Right => self.move_cursor(key == Key::Left),
                _ => {}
            },
            Language::Korean => match key {
                Key::Char(c) => self.hangul.input(jamo_of_key(c).unwrap_or(c)),
                Key::Space => self.hangul.input(' '),
                Key::Backspace => {
                    if !self.hangul.backspace() {
                        self.text.pop();
                    }
                }
                // the syllable being made is written first, then the cursor moves
                Key::Left | Key::Right => {
                    self.text += &self.hangul.take();
                    self.move_cursor(key == Key::Left);
                }
                _ => {}
            },
            Language::Japanese | Language::Chinese => self.rime_key(key),
        }
    }

    fn rime_key(&mut self, key: Key) {
        if self.session().is_none() {
            return;
        }
        let composing = self.composing();
        // what only the text takes
        match key {
            // RIME types the readings (romaji, pinyin; ー, and ' between pinyin syllables). The rest
            // goes after what is composed: digits (RIME picks a candidate with them), punctuation
            // (RIME's own pages candidates with . and commits with others, some converted, some
            // not) and capitals (jaroomaji makes Shift katakana letter by letter)
            Key::Char(c) if !(c.is_ascii_lowercase() || (c == '-' && self.language == Language::Japanese)
                || (c == '\'' && self.language == Language::Chinese && composing)) => {
                self.flush();
                // 1.5 and 1,000 stay as typed
                let after_digit = self.text.ends_with(|t: char| t.is_ascii_digit());
                self.text.push(if after_digit && (c == '.' || c == ',') { c } else { full_width(self.language, c) });
                return;
            }
            Key::Space if !composing => {
                self.text.push(' ');
                return;
            }
            Key::Backspace if !composing => {
                self.text.pop();
                return;
            }
            Key::Enter if !composing => return,
            // while composing, RIME moves between the segments
            Key::Left | Key::Right if !composing => {
                self.move_cursor(key == Key::Left);
                return;
            }
            _ => {}
        }
        // Japanese as Japanese keyboards do: 変換 shows the first candidate, then the next ones;
        // 確定 takes the one shown, the kana before 変換 (jaroomaji's own Space would commit)
        let japanese = self.language == Language::Japanese;
        let converting = self.converting;
        if let Key::Char(_) | Key::Backspace = key {
            self.converting = false;
        }
        let Some(s) = self.session() else { return };
        let taken = match key {
            Key::Char(c) => s.key(c as i32, 0),
            Key::Space if japanese => {
                if converting {
                    s.key(keys::DOWN, 0);
                }
                self.converting = true;
                return;
            }
            Key::Enter if japanese && converting => s.select(s.context().highlighted),
            Key::Space => s.key(keys::SPACE, 0),
            Key::Enter => s.key(keys::RETURN, 0),
            Key::Backspace => s.key(keys::BACKSPACE, 0),
            Key::Left => s.key(keys::LEFT, 0),
            Key::Right => s.key(keys::RIGHT, 0),
            Key::PageUp => s.key(keys::PAGE_UP, 0),
            Key::PageDown => s.key(keys::PAGE_DOWN, 0),
        };
        if let (Key::Char(c), false) = (key, taken) {
            self.text.push(c);
        }
        self.collect();
    }

    /// The cursor to this character of the text (the input box pressed there). Not while a word is
    /// being composed (it is chosen first); Korean's syllable being made is written first
    pub fn set_cursor(&mut self, index: usize) {
        if self.composing() {
            return;
        }
        self.text += &self.hangul.take();
        let all = std::mem::take(&mut self.text) + &std::mem::take(&mut self.after);
        let at = all.char_indices().nth(index).map_or(all.len(), |(i, _)| i);
        self.text = all[..at].into();
        self.after = all[at..].into();
    }

    /// A character across the cursor
    fn move_cursor(&mut self, left: bool) {
        if left {
            if let Some(c) = self.text.pop() {
                self.after.insert(0, c);
            }
        } else if let Some(c) = self.after.chars().next() {
            self.after.remove(0);
            self.text.push(c);
        }
    }

    /// The candidate at `index` of the page shown
    pub fn select(&mut self, index: usize) {
        if let Some(s) = self.session() {
            s.select(index);
        }
        // the rest, if any, is being converted
        self.converting = true;
        self.collect();
    }

    /// Text that could not be sent goes back, before what was typed since
    pub fn restore(&mut self, text: &str) {
        self.text.insert_str(0, text);
    }

    /// The text replaced by this (a message sent before, called back): what was being composed is dropped
    pub fn set_text(&mut self, text: &str) {
        self.clear();
        self.text = text.into();
    }

    /// Text from elsewhere (what the microphone heard) at the cursor, with a space between words
    /// of Latin letters; what is being composed stays after it (Korean's syllables are written first)
    pub fn append(&mut self, text: &str) {
        self.text += &self.hangul.take();
        let text = text.trim();
        let ends_word = self.text.chars().last().is_some_and(|c| c.is_ascii_alphanumeric() || ".,!?".contains(c));
        if ends_word && text.starts_with(|c: char| c.is_ascii_alphanumeric()) {
            self.text.push(' ');
        }
        self.text += text;
    }

    /// The whole text (what is being composed included), then empty
    pub fn take(&mut self) -> String {
        self.flush();
        std::mem::take(&mut self.text) + &std::mem::take(&mut self.after)
    }

    pub fn clear(&mut self) {
        if let Some(s) = &self.rime {
            s.clear();
        }
        self.hangul.take();
        self.text.clear();
        self.after.clear();
        self.converting = false;
    }

    pub fn state(&self) -> State {
        let mut state = State { text: self.text.clone(), after: self.after.clone(), ..Default::default() };
        let mut composed = 0;
        if let Some(s) = self.session() {
            let c = s.context();
            if !c.preedit.is_empty() {
                composed = c.preedit.chars().count();
                state.composition = Some(Composition { preedit: c.preedit, selection: c.selection, cursor: c.cursor });
                state.candidates = c.candidates;
                state.highlighted = c.highlighted;
                state.converting = self.converting;
                state.page = c.page;
                state.last_page = c.last_page;
            }
        }
        if self.language == Language::Korean {
            // the syllables done are text; the one being made shows after it
            state.text += self.hangul.written();
            state.syllable = self.hangul.composing();
            composed = state.syllable.as_ref().map_or(0, |(s, _)| s.chars().count());
        }
        state.length = state.text.chars().count() + state.after.chars().count() + composed;
        state
    }
}

/// The punctuation the keyboard types, as Japanese / Chinese text writes it (the rest as typed)
fn full_width(language: Language, c: char) -> char {
    let table: &[(char, char)] = match language {
        Language::Japanese => &[(',', '、'), ('.', '。'), ('?', '？'), ('!', '！'), ('[', '「'), (']', '」'), ('/', '・'), ('~', '〜')],
        Language::Chinese => &[(',', '，'), ('.', '。'), ('?', '？'), ('!', '！'), ('[', '「'), (']', '」'), (';', '；'), (':', '：'),
                               ('(', '（'), (')', '）'), ('\\', '、')],
        _ => &[],
    };
    table.iter().find(|(from, _)| *from == c).map_or(c, |(_, to)| *to)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn typed(input: &mut Input, s: &str) {
        for c in s.chars() {
            input.key(if c == ' ' { Key::Space } else { Key::Char(c) });
        }
    }

    #[test]
    fn english_goes_in_as_typed() {
        let mut i = Input::new(Language::English);
        typed(&mut i, "Hi there");
        i.key(Key::Backspace);
        assert_eq!(i.state().text, "Hi ther");
        assert_eq!(i.state().length, 7);
        assert_eq!(i.take(), "Hi ther");
        assert_eq!(i.state().text, "");
    }

    #[test]
    fn korean_composes_and_shows_the_syllable_being_made() {
        let mut i = Input::new(Language::Korean);
        typed(&mut i, "dkssudgktpd");
        let s = i.state();
        assert_eq!(s.text, "안녕하");
        assert_eq!(s.syllable, Some(("셍".to_string(), vec!['ㅅ', 'ㅔ', 'ㅇ'])));
        assert_eq!(s.length, 4);
        typed(&mut i, "y");
        assert_eq!(i.take(), "안녕하세요");
    }

    #[test]
    fn switching_language_keeps_what_was_written() {
        let mut i = Input::new(Language::Korean);
        typed(&mut i, "gksrmf");
        i.set_language(Language::English);
        typed(&mut i, " ok");
        assert_eq!(i.take(), "한글 ok");
    }

    #[test]
    fn text_not_sent_goes_back_before_what_was_typed_since() {
        let mut i = Input::new(Language::English);
        typed(&mut i, "hello");
        let sent = i.take();
        typed(&mut i, " again");
        i.restore(&sent);
        assert_eq!(i.take(), "hello again");
    }

    #[test]
    fn a_line_break_is_text_in_every_language() {
        let mut i = Input::new(Language::English);
        typed(&mut i, "hi\nok");
        assert_eq!(i.state().length, 5);
        for _ in 0..3 {
            i.key(Key::Backspace);
        }
        assert_eq!(i.take(), "hi");
        // Korean: the break ends the syllable being made
        let mut i = Input::new(Language::Korean);
        typed(&mut i, "gks\nrmf");
        assert_eq!(i.take(), "한\n글");
    }

    #[test]
    fn a_text_called_back_replaces_and_heard_text_is_appended() {
        let mut i = Input::new(Language::Korean);
        typed(&mut i, "gks");
        i.set_text("hello");
        assert_eq!(i.state().syllable, None);
        i.append(" world ");
        i.append("。ok");
        assert_eq!(i.take(), "hello world。ok");
        i.set_text("日本");
        i.append("語");
        assert_eq!(i.take(), "日本語");
        // Korean typed before it stays before it
        typed(&mut i, "gksrmf");
        i.append("hello");
        assert_eq!(i.take(), "한글hello");
    }

    #[test]
    fn left_and_right_move_the_cursor_and_typing_goes_there() {
        let mut i = Input::new(Language::English);
        typed(&mut i, "helo");
        i.key(Key::Left);
        typed(&mut i, "l");
        i.key(Key::Left);
        i.key(Key::Left);
        i.key(Key::Backspace);
        let s = i.state();
        assert_eq!((s.text.as_str(), s.after.as_str(), s.length), ("h", "llo", 4));
        // past the ends: nothing moves
        for _ in 0..3 {
            i.key(Key::Left);
        }
        typed(&mut i, "H");
        for _ in 0..9 {
            i.key(Key::Right);
        }
        typed(&mut i, "!");
        assert_eq!(i.take(), "Hhllo!");
        // put where the input box was pressed (past the end: at the end)
        typed(&mut i, "日本語です");
        i.set_cursor(2);
        typed(&mut i, "の");
        i.set_cursor(99);
        typed(&mut i, "!");
        assert_eq!(i.take(), "日本の語です!");
        // Korean: the syllable being made is written before the cursor moves
        let mut i = Input::new(Language::Korean);
        typed(&mut i, "gksrmf");
        i.key(Key::Left);
        typed(&mut i, "dk");
        assert_eq!(i.take(), "한아글");
    }

    #[test]
    fn japanese_waits_for_the_dictionaries() {
        let mut i = Input::new(Language::Japanese);
        assert!(!i.available(Language::Japanese));
        assert!(i.available(Language::English));
        typed(&mut i, "nihongo");
        assert_eq!(i.state(), State::default());
    }
}
