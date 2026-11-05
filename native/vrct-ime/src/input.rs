//! What the keyboard holds while typing: the text written so far and the word being composed,
//! by language. English goes in as typed, Korean through the Hangul composer, Japanese and
//! Chinese (pinyin, Zhuyin, Cangjie, Quick) through a RIME session (when the dictionaries are ready).
//! The text has a selection (Shift ◀ ▶, Ctrl+A) that typing replaces, and its edits undo and redo.
use crate::kana;
use crate::hangul::{jamo_of_key, Composer};
use crate::rime::{keys, Session};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Language {
    Japanese,
    English,
    Korean,
    /// pinyin
    Chinese,
    /// Zhuyin (Bopomofo, the Dachen layout)
    Zhuyin,
    Cangjie,
    /// Quick (Cangjie's first and last codes)
    Quick,
}

impl Language {
    pub fn from_code(code: &str) -> Option<Language> {
        Some(match code {
            "ja" => Language::Japanese,
            "en" => Language::English,
            "ko" => Language::Korean,
            "zh" => Language::Chinese,
            "zhuyin" => Language::Zhuyin,
            "cangjie" => Language::Cangjie,
            "quick" => Language::Quick,
            _ => return None,
        })
    }

    pub fn code(self) -> &'static str {
        match self {
            Language::Japanese => "ja",
            Language::English => "en",
            Language::Korean => "ko",
            Language::Chinese => "zh",
            Language::Zhuyin => "zhuyin",
            Language::Cangjie => "cangjie",
            Language::Quick => "quick",
        }
    }

    /// The RIME schema it types with (None: no dictionary needed)
    pub fn schema(self) -> Option<&'static str> {
        match self {
            Language::Japanese => Some("jaroomaji"),
            Language::Chinese => Some("luna_pinyin"),
            Language::Zhuyin => Some("bopomofo"),
            Language::Cangjie => Some("cangjie5"),
            Language::Quick => Some("quick5"),
            _ => None,
        }
    }

    /// Whether RIME types `c` (`composing`: a word is being composed): the readings and codes (romaji,
    /// pinyin with ー for Japanese and ' between pinyin syllables; Zhuyin's keys, digits and , . ; / -
    /// included; Cangjie's radicals). The rest goes after what is composed: digits (RIME picks a
    /// candidate with them), punctuation (RIME's own pages candidates with . and commits with others,
    /// some converted, some not) and capitals (jaroomaji makes Shift katakana letter by letter)
    fn rime_types(self, c: char, composing: bool) -> bool {
        c.is_ascii_lowercase() || match self {
            Language::Japanese => c == '-',
            Language::Chinese => c == '\'' && composing,
            Language::Zhuyin => c.is_ascii_digit() || ",.;/-".contains(c),
            _ => false,
        }
    }

    /// Its table of punctuation in keys.yaml (None: as typed)
    fn punctuation(self) -> Option<&'static str> {
        match self {
            Language::Japanese => Some("ja"),
            Language::Chinese | Language::Cangjie | Language::Quick => Some("zh"),
            Language::Zhuyin => Some("zhuyin"),
            Language::English | Language::Korean => None,
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
    /// 半角/全角: Japanese typed as it is (half-width, the JIS keys kept) or back to kana
    HalfWidth,
    /// the candidate highlighted taken (Japanese, Chinese; nothing when not composing)
    Tab,
    /// ◀ ▶ with Ctrl (to the word's edge) and / or Shift (selecting from where the cursor was)
    Move { left: bool, word: bool, select: bool },
    SelectAll,
    /// the last edit undone (typing in a row is one); what is being composed is dropped first
    Undo,
    Redo,
}

/// What an edit was: typing (or deleting) in a row undoes as one
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Edit {
    None,
    Typing,
    Deleting,
    Other,
}

/// The text as it was, for undo and redo (the cursor where it was)
#[derive(Clone, Debug)]
struct Snapshot {
    text: String,
    after: String,
}

/// The edits kept to undo
const UNDO_LIMIT: usize = 100;

/// The word being composed (Japanese, Chinese): as shown, and the segment being chosen
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Composition {
    pub preedit: String,
    /// Editing cursor in displayed Unicode characters.
    pub cursor: usize,
    pub selection: (usize, usize),
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
    /// Korean: the syllable being made (at the cursor)
    pub syllable: Option<String>,
    /// characters of the text (both sides of the cursor) and what is being composed (VRChat's chat box takes 144)
    pub length: usize,
    /// Japanese typed as it is (半角/全角)
    pub half_width: bool,
    /// characters selected before the cursor (the end of `text`) and after it (the start of `after`)
    pub selected: (usize, usize),
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
    /// Whole-number width candidates use the same conversion controls as RIME candidates.
    numeric_candidate: usize,
    /// Japanese typed as English is (半角/全角), until pressed again or the language changes
    half_width: bool,
    /// where the selection began (a character of text + after); the cursor is its other end
    anchor: Option<usize>,
    undo: Vec<Snapshot>,
    redo: Vec<Snapshot>,
    last_edit: Edit,
}

impl<'r> Input<'r> {
    pub fn new(language: Language) -> Self {
        Self { text: String::new(), after: String::new(), language, rime: None, hangul: Composer::new(), converting: false, numeric_candidate: 0, half_width: false,
               anchor: None, undo: Vec::new(), redo: Vec::new(), last_edit: Edit::None }
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
            self.finish_composition();
            self.language = language;
            self.half_width = false;
            self.select_schema();
        }
    }

    /// Finish an input-method change in the editor, without sending the text.
    pub fn finish_composition(&mut self) {
        let before = self.snapshot();
        self.flush();
        self.converting = false;
        self.record(before, Edit::Other);
        self.last_edit = Edit::None;
    }

    pub fn set_simplified(&self, simplified: bool) {
        if let Some(s) = &self.rime {
            // the Chinese schemas' switch: Simplified through OpenCC (zh_hans: pinyin and Zhuyin;
            // simplification: Cangjie and Quick)
            s.set_option("zh_hans", simplified);
            s.set_option("simplification", simplified);
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
        if self.converting && self.select_numeric(self.numeric_candidate) {
            return;
        }
        let kana = self.language == Language::Japanese && !self.converting;
        if let Some(s) = self.session() {
            if !s.input().is_empty() {
                if kana {
                    // Return commits only the portion before RIME's caret. Finish the whole
                    // reading when switching input methods or leaving the composition.
                    s.set_caret(s.input().len());
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
        match key {
            Key::Undo => return self.undo(),
            Key::Redo => return self.redo(),
            _ => {}
        }
        let before = self.snapshot();
        self.edit_key(key);
        let kind = match key {
            Key::Char(_) | Key::Space => Edit::Typing,
            Key::Backspace => Edit::Deleting,
            Key::Enter | Key::Tab => Edit::Other,
            _ => Edit::None,
        };
        self.record(before, kind);
    }

    fn edit_key(&mut self, key: Key) {
        match key {
            Key::HalfWidth => {
                if self.language == Language::Japanese {
                    self.flush();
                    self.half_width = !self.half_width;
                }
                return;
            }
            Key::Move { left, word, select } => {
                self.flush();
                self.move_by(left, word, select);
                return;
            }
            Key::SelectAll => {
                self.flush();
                self.text += &std::mem::take(&mut self.after);
                self.anchor = Some(0);
                return;
            }
            Key::Tab => {
                if self.numeric_candidates().is_some() {
                    self.select(if self.converting { self.numeric_candidate } else { 0 });
                } else if let Some(s) = self.session().filter(|_| self.composing()) {
                    let highlighted = s.context().highlighted;
                    self.select(highlighted);
                }
                return;
            }
            _ => {}
        }
        // a selection: ◀ ▶ go to its ends, Backspace deletes it, typing replaces it
        if let Some((start, end)) = self.selection() {
            match key {
                Key::Left | Key::Right => {
                    self.anchor = None;
                    self.place(if key == Key::Left { start } else { end });
                    return;
                }
                Key::Backspace => {
                    self.delete_selection();
                    return;
                }
                Key::Char(_) | Key::Space => {
                    self.delete_selection();
                }
                _ => {}
            }
        }
        self.anchor = None;
        let language = if self.half_width { Language::English } else { self.language };
        match language {
            Language::English => match key {
                Key::Char(c) => self.text.push(c),
                Key::Space => self.text.push(' '),
                Key::Backspace => {
                    self.text.pop();
                }
                Key::Left | Key::Right => self.move_cursor(key == Key::Left),
                _ => {}
            },
            // the syllables done go into the text at once; the one being made is at the cursor
            Language::Korean => match key {
                Key::Char(c) => self.text += &self.hangul.input(jamo_of_key(c).unwrap_or(c)),
                Key::Space => self.text += &self.hangul.input(' '),
                Key::Backspace => {
                    if !self.hangul.backspace() {
                        self.text.pop();
                    }
                }
                // the syllable being made is finished first, then the cursor moves
                Key::Left | Key::Right => {
                    self.text += &self.hangul.take();
                    self.move_cursor(key == Key::Left);
                }
                _ => {}
            },
            Language::Japanese | Language::Chinese | Language::Zhuyin | Language::Cangjie | Language::Quick => self.rime_key(key),
        }
    }

    fn rime_key(&mut self, key: Key) {
        if self.session().is_none() {
            return;
        }
        let composing = self.composing();
        if let Some(candidates) = self.numeric_candidates() {
            match key {
                Key::Space => {
                    self.numeric_candidate = if self.converting { (self.numeric_candidate + 1) % candidates.len() } else { 0 };
                    self.converting = true;
                    return;
                }
                Key::Enter if self.converting => {
                    self.select_numeric(self.numeric_candidate);
                    return;
                }
                Key::PageUp | Key::PageDown => return, // the width choices fit on one page
                Key::Left | Key::Right => {
                    self.numeric_candidate = 0;
                    self.converting = false;
                }
                _ => {}
            }
        }
        if self.language == Language::Japanese {
            if let Key::Char(c) = key {
                if crate::punctuation::supported(c) {
                    let before_caret = self.session().map(|s| s.context()).and_then(|context|
                        context.preedit.chars().take(context.cursor).last());
                    let after_digit = before_caret.or_else(|| self.text.chars().last()).is_some_and(|c| c.is_ascii_digit() || matches!(c, '０'..='９'));
                    self.insert_punctuation(if after_digit && matches!(c, '.' | ',') { c }
                        else if c == '-' { 'ー' }
                        else { full_width(self.language, c) });
                    return;
                }
            }
        }
        // what only the text takes
        match key {
            Key::Char(c) if !self.language.rime_types(c, composing) => {
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
        if japanese && key == Key::Backspace {
            self.converting = false;
            if !converting {
                self.backspace_kana();
            }
            self.collect();
            return;
        }
        if let Key::Char(_) | Key::Backspace = key {
            self.converting = false;
        }
        let Some(s) = self.session() else { return };
        let taken = match key {
            Key::Char(c) if japanese => Self::japanese_char(s, c),
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
            Key::HalfWidth | Key::Tab | Key::Move { .. } | Key::SelectAll | Key::Undo | Key::Redo => return,
        };
        if let (Key::Char(c), false) = (key, taken) {
            self.text.push(c);
        }
        self.collect();
    }

    /// Only expand a pending consonant in ordinary romaji input. Flick and editing already
    /// send canonical spellings, and must not re-expand their intermediate characters.
    fn japanese_char(s: &Session<'_>, next: char) -> bool {
        let context = s.context();
        let pending: String = context.preedit.chars().take(context.cursor).skip(context.selection.0).collect();
        let back = if "kcqgszjtdhfbvpmyrw".contains(next) && pending.ends_with(next) {
            1
        } else if next == 'h' && pending.ends_with("tc") {
            2
        } else {
            return s.key(next as i32, 0);
        };
        let before_caret = s.caret();
        let taken = s.key(next as i32, 0);
        if !taken { return false; }
        let mut raw = s.input();
        let caret = s.caret();
        if before_caret < back || caret != before_caret + 1 || caret > raw.len() { return true; }
        let start = before_caret - back;
        if !raw.is_char_boundary(start) { return true; }
        if (back == 1 && raw.as_bytes()[start] != next as u8) || (back == 2 && &raw[start..before_caret] != "tc") { return true; }
        let original = raw.clone();
        let mut expected: Vec<char> = context.preedit.chars().collect();
        expected[context.cursor - back] = 'っ';
        expected.insert(context.cursor, next);
        let expected: String = expected.into_iter().collect();
        raw.replace_range(start..start + 1, "xtu");
        if s.set_input(&raw) {
            s.set_caret(caret + 2);
            let expanded = s.context();
            // An invalid preceding syllable (e.g. hhjj) can leave the expanded xtu
            // outside RIME's translated segment. Only accept the intended small-tsu
            // replacement, retaining the rest of the displayed reading and cursor.
            if expanded.preedit != expected || expanded.cursor != context.cursor + 1 {
                s.set_input(&original);
                s.set_caret(caret);
            }
        }
        true
    }

    /// Remove one displayed character, preserving RIME's selected segments and cursor.
    /// A contracted spelling (kya) may need to be shortened and retyped (ki).
    fn backspace_kana(&self) {
        let Some(s) = self.session() else { return };
        let context = s.context();
        let mut left: String = context.preedit.chars().take(context.cursor).collect();
        let Some(removed) = left.pop() else { return };
        if crate::punctuation::supported(removed) && context.cursor > context.selection.0 {
            let mut raw = s.input();
            let caret = s.caret();
            if let Some((_, code, _)) = crate::punctuation::entries().find(|(_, code, _)| raw.get(..caret).is_some_and(|before| before.ends_with(code))) {
                let start = caret - code.len();
                raw.replace_range(start..caret, "");
                s.set_input(&raw);
                s.set_caret(start);
                return;
            }
        }
        if context.cursor <= context.selection.0 || (kana::romaji(removed).is_none() && !removed.is_ascii_lowercase()) {
            s.key(keys::BACKSPACE, 0);
            return;
        }
        let right: String = context.preedit.chars().skip(context.cursor).collect();
        let original = s.input();
        let original_caret = s.caret();
        if !original.is_char_boundary(original_caret) { return; }
        let mut raw = original.clone();
        let protected: String = context.preedit.chars().take(context.selection.0).collect();
        for (caret, _) in original[..original_caret].char_indices().rev() {
            raw.remove(caret);
            if !s.set_input(&raw) { break; }
            s.set_caret(caret);
            let current = s.context();
            let prefix: String = current.preedit.chars().take(current.cursor).collect();
            let suffix: String = current.preedit.chars().skip(current.cursor).collect();
            // At the beginning RIME displays the untouched suffix as kana again.
            if left.is_empty() && caret == 0 && raw == original[original_caret..] {
                return;
            }
            if let Some(rest) = left.strip_prefix(&prefix).filter(|_| suffix == right
                || (caret == 0 && raw == original[original_caret..])) {
                let romaji: Option<String> = rest.chars().map(|c| kana::romaji(c).map(str::to_owned)
                    .or_else(|| c.is_ascii_lowercase().then(|| c.to_string()))).collect();
                if let Some(romaji) = romaji {
                    let mut replacement = raw.clone();
                    replacement.insert_str(caret, &romaji);
                    s.set_input(&replacement);
                    s.set_caret(caret + romaji.len());
                    let result = s.context();
                    if result.preedit == left.clone() + &right && result.cursor == left.chars().count() {
                        return;
                    }
                    break;
                }
            }
            // Never search back into a segment the user already selected.
            if prefix == protected || !prefix.starts_with(&protected) { break; }
        }
        // An unfamiliar spelling or cursor boundary must not discard surrounding text.
        s.set_input(&original);
        s.set_caret(original_caret);
    }

    /// The cursor to this character of the text (the input box pressed there). Not while a word is
    /// being composed (it is chosen first); Korean's syllable being made is finished first
    pub fn set_cursor(&mut self, index: usize) {
        if self.composing() {
            return;
        }
        let before = self.snapshot();
        self.text += &self.hangul.take();
        self.anchor = None;
        self.place(index);
        self.record(before, Edit::None);
    }

    /// The cursor to this character of the text
    fn place(&mut self, index: usize) {
        let all = std::mem::take(&mut self.text) + &std::mem::take(&mut self.after);
        let at = all.char_indices().nth(index).map_or(all.len(), |(i, _)| i);
        self.text = all[..at].into();
        self.after = all[at..].into();
    }

    fn cursor(&self) -> usize {
        self.text.chars().count()
    }

    /// The characters selected (start, end), if any
    fn selection(&self) -> Option<(usize, usize)> {
        let cursor = self.cursor();
        self.anchor.filter(|&a| a != cursor).map(|a| (a.min(cursor), a.max(cursor)))
    }

    /// ◀ ▶: a character or to the word's edge; selecting keeps where the selection began, not
    /// selecting ends it (a character's move to its end, as Windows does)
    fn move_by(&mut self, left: bool, word: bool, select: bool) {
        let cursor = self.cursor();
        if select {
            self.anchor.get_or_insert(cursor);
        } else if let Some((start, end)) = self.selection().filter(|_| !word) {
            self.anchor = None;
            return self.place(if left { start } else { end });
        } else {
            self.anchor = None;
        }
        let all: Vec<char> = self.text.chars().chain(self.after.chars()).collect();
        let to = match (word, left) {
            (true, _) => word_edge(&all, cursor, left),
            (false, true) => cursor.saturating_sub(1),
            (false, false) => (cursor + 1).min(all.len()),
        };
        self.place(to);
    }

    fn delete_selection(&mut self) {
        if let Some((start, end)) = self.selection() {
            let all: Vec<char> = self.text.chars().chain(self.after.chars()).collect();
            self.text = all[..start].iter().collect();
            self.after = all[end..].iter().collect();
            // what is typed next is an edit of its own
            self.last_edit = Edit::None;
        }
        self.anchor = None;
    }

    /// The text selected (Ctrl+C), if any
    pub fn selected_text(&self) -> Option<String> {
        let (start, end) = self.selection()?;
        Some(self.text.chars().chain(self.after.chars()).skip(start).take(end - start).collect())
    }

    /// The selection deleted (Ctrl+X, once it is on the clipboard)
    pub fn cut(&mut self) {
        let before = self.snapshot();
        self.delete_selection();
        self.record(before, Edit::Other);
    }

    /// Ctrl+V: `text` in place of the selection, at the cursor (what was being composed written
    /// first; line ends as \n, tabs as spaces, other control characters dropped)
    pub fn paste(&mut self, text: &str) {
        let before = self.snapshot();
        self.flush();
        self.delete_selection();
        let text = text.replace("\r\n", "\n").replace('\r', "\n").replace('\t', " ");
        self.text.extend(text.chars().filter(|c| *c == '\n' || !c.is_control()));
        self.record(before, Edit::Other);
    }

    fn insert_punctuation(&mut self, c: char) {
        let Some(s) = self.session() else { return };
        let Some(code) = crate::punctuation::spelling(c) else { return };
        let mut raw = s.input();
        let caret = s.caret();
        if !raw.is_char_boundary(caret) { return; }
        raw.insert_str(caret, &code);
        if s.set_input(&raw) {
            s.set_caret(caret + code.len());
        }
        self.converting = false;
        self.collect();
    }

    fn snapshot(&self) -> Snapshot {
        Snapshot { text: self.text.clone(), after: self.after.clone() }
    }

    /// After an edit: the text as it was before is kept to undo (typing or deleting in a row
    /// keeps only the first); anything else ends the run
    fn record(&mut self, before: Snapshot, kind: Edit) {
        // the same text with the cursor elsewhere is not an edit
        if before.text.clone() + &before.after == self.text.clone() + &self.after {
            if kind == Edit::None {
                self.last_edit = Edit::None;
            }
            return;
        }
        if !(kind == self.last_edit && matches!(kind, Edit::Typing | Edit::Deleting)) {
            self.undo.push(before);
            if self.undo.len() > UNDO_LIMIT {
                self.undo.remove(0);
            }
        }
        self.redo.clear();
        self.last_edit = if kind == Edit::Other { Edit::None } else { kind };
    }

    /// Ctrl+Z: what is being composed is dropped, else the text as it was before the last edit
    fn undo(&mut self) {
        if self.composing() || self.hangul.composing().is_some() {
            if let Some(s) = self.session() {
                s.clear();
            }
            self.hangul.take();
            self.converting = false;
            return;
        }
        if let Some(s) = self.undo.pop() {
            self.redo.push(self.snapshot());
            self.go_back_to(s);
        }
    }

    /// Ctrl+Y
    fn redo(&mut self) {
        if self.composing() {
            return;
        }
        if let Some(s) = self.redo.pop() {
            self.undo.push(self.snapshot());
            self.go_back_to(s);
        }
    }

    fn go_back_to(&mut self, s: Snapshot) {
        self.hangul.take();
        self.text = s.text;
        self.after = s.after;
        self.anchor = None;
        self.last_edit = Edit::None;
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
        if self.numeric_candidates().is_some() {
            self.select_numeric(index);
            return;
        }
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
        let before = self.snapshot();
        self.reset();
        self.text = text.into();
        self.record(before, Edit::Other);
    }

    /// Text from elsewhere (what the microphone heard) at the cursor, with a space between words
    /// of Latin letters; what is being composed stays after it (Korean's syllable is finished first)
    pub fn append(&mut self, text: &str) {
        let before = self.snapshot();
        self.delete_selection();
        self.text += &self.hangul.take();
        let text = text.trim();
        let ends_word = self.text.chars().last().is_some_and(|c| c.is_ascii_alphanumeric() || ".,!?".contains(c));
        if ends_word && text.starts_with(|c: char| c.is_ascii_alphanumeric()) {
            self.text.push(' ');
        }
        self.text += text;
        self.record(before, Edit::Other);
    }

    /// The whole text (what is being composed included), then empty (to send: nothing to undo)
    pub fn take(&mut self) -> String {
        self.flush();
        self.anchor = None;
        self.undo.clear();
        self.redo.clear();
        self.last_edit = Edit::None;
        std::mem::take(&mut self.text) + &std::mem::take(&mut self.after)
    }

    /// Everything typed gone (Ctrl+Z brings it back)
    pub fn clear(&mut self) {
        let before = self.snapshot();
        self.reset();
        self.record(before, Edit::Other);
    }

    fn reset(&mut self) {
        if let Some(s) = &self.rime {
            s.clear();
        }
        self.hangul.take();
        self.text.clear();
        self.after.clear();
        self.converting = false;
        self.anchor = None;
    }

    pub fn state(&self) -> State {
        let mut state = State { text: self.text.clone(), after: self.after.clone(), ..Default::default() };
        let mut composed = 0;
        if let Some(s) = self.session() {
            let c = s.context();
            if !c.preedit.is_empty() {
                composed = c.preedit.chars().count();
                state.composition = Some(Composition { preedit: c.preedit, cursor: c.cursor, selection: c.selection });
                state.candidates = c.candidates;
                state.highlighted = c.highlighted;
                state.converting = self.converting;
                state.page = c.page;
                state.last_page = c.last_page;
            }
        }
        if let Some(candidates) = self.numeric_candidates() {
            state.candidates = candidates;
            state.highlighted = if self.converting { self.numeric_candidate.min(state.candidates.len() - 1) } else { 0 };
            state.page = 0;
            state.last_page = true;
            if let Some(composition) = &mut state.composition {
                composition.selection = (0, composition.preedit.chars().count());
            }
        }
        if self.language == Language::Korean {
            state.syllable = self.hangul.composing();
            composed = state.syllable.as_ref().map_or(0, |s| s.chars().count());
        }
        state.length = state.text.chars().count() + state.after.chars().count() + composed;
        state.half_width = self.half_width;
        if let Some((start, end)) = self.selection() {
            let cursor = self.cursor();
            state.selected = (cursor - start, end - cursor);
        }
        state
    }

    /// Only a complete, unsegmented number at its end gets whole-number width choices.
    /// Mixed Japanese text and partially selected segments keep RIME's ordinary segmentation.
    fn numeric_candidates(&self) -> Option<Vec<String>> {
        if self.language != Language::Japanese || self.half_width { return None; }
        let context = self.session()?.context();
        if context.selection.0 != 0 || context.cursor != context.preedit.chars().count() { return None; }
        number_widths(&context.preedit)
    }

    fn select_numeric(&mut self, index: usize) -> bool {
        let Some(candidates) = self.numeric_candidates() else { return false };
        let Some(selected) = candidates.get(index) else { return false };
        let Some(s) = self.session() else { return false };
        let Some(raw) = selected.chars().map(crate::punctuation::spelling).collect::<Option<String>>() else { return false };
        if !s.set_input(&raw) { return false; }
        s.set_caret(raw.len());
        s.key(keys::RETURN, 0);
        self.collect();
        true
    }
}

fn number_widths(reading: &str) -> Option<Vec<String>> {
    let half: String = reading.chars().map(|c| match c {
        '０'..='９' => char::from_u32(c as u32 - '０' as u32 + '0' as u32).unwrap(),
        '．' => '.', '，' => ',', _ => c,
    }).collect();
    let (integer, fraction) = half.split_once('.').map_or((half.as_str(), None), |(a, b)| (a, Some(b)));
    let digits = |s: &str| !s.is_empty() && s.bytes().all(|c| c.is_ascii_digit());
    if !fraction.is_none_or(digits) { return None; }
    let groups: Vec<&str> = integer.split(',').collect();
    if !groups.iter().all(|s| digits(s)) || (groups.len() > 1 && (groups[0].len() > 3 || groups[1..].iter().any(|s| s.len() != 3))) {
        return None;
    }
    let full: String = half.chars().map(|c| match c {
        '0'..='9' => char::from_u32(c as u32 - '0' as u32 + '０' as u32).unwrap(),
        '.' => '．', ',' => '，', _ => c,
    }).collect();
    let mut candidates = vec![reading.to_string()];
    for candidate in [half, full] {
        if !candidates.contains(&candidate) { candidates.push(candidate); }
    }
    Some(candidates)
}

/// Ctrl ◀ ▶: from `at` over the spaces and one run of the same kind of characters (letters and
/// digits, hiragana, katakana, kanji, hangul, other symbols), as Windows moves by words
fn word_edge(chars: &[char], at: usize, left: bool) -> usize {
    fn kind(c: char) -> u8 {
        match c {
            'ぁ'..='ゖ' | 'ゝ' | 'ゞ' => 1,
            'ァ'..='ヺ' | 'ー' | 'ヽ' | 'ヾ' | 'ｦ'..='ﾟ' => 2,
            '\u{3400}'..='\u{4DBF}' | '\u{4E00}'..='\u{9FFF}' | '々' | '〆' => 3,
            '\u{1100}'..='\u{11FF}' | '\u{3130}'..='\u{318F}' | '\u{AC00}'..='\u{D7A3}' => 4,
            c if c.is_alphanumeric() || c == '_' => 5,
            _ => 6,
        }
    }
    let mut i = at;
    if left {
        while i > 0 && chars[i - 1].is_whitespace() {
            i -= 1;
        }
        if let Some(k) = i.checked_sub(1).map(|j| kind(chars[j])) {
            while i > 0 && !chars[i - 1].is_whitespace() && kind(chars[i - 1]) == k {
                i -= 1;
            }
        }
    } else {
        if let Some(k) = chars.get(i).filter(|c| !c.is_whitespace()).map(|c| kind(*c)) {
            while i < chars.len() && !chars[i].is_whitespace() && kind(chars[i]) == k {
                i += 1;
            }
        }
        while i < chars.len() && chars[i].is_whitespace() {
            i += 1;
        }
    }
    i
}

/// The punctuation the keyboard types, as Japanese / Chinese text writes it (keys.yaml; the rest as typed)
fn full_width(language: Language, c: char) -> char {
    let Some(table) = language.punctuation() else { return c };
    crate::keys::mapped(&["punctuation", table], c).unwrap_or(c)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn number_candidates_cover_whole_valid_numbers_only() {
        assert_eq!(number_widths("123").unwrap(), ["123", "１２３"]);
        assert_eq!(number_widths("1,000.5").unwrap(), ["1,000.5", "１，０００．５"]);
        assert_eq!(number_widths("１２３").unwrap(), ["１２３", "123"]);
        for invalid in ["", "k123", "1.", ".5", "1,00", "1234,567", "1.2.3", "１２a"] {
            assert!(number_widths(invalid).is_none(), "{invalid}");
        }
    }

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
        assert_eq!(s.syllable.as_deref(), Some("셍"));
        assert_eq!(s.length, 4);
        typed(&mut i, "y");
        assert_eq!(i.take(), "안녕하세요");
        // Backspace: a jamo of the syllable being made, then whole syllables done
        typed(&mut i, "gksrmf");
        for _ in 0..3 {
            i.key(Key::Backspace);
        }
        assert_eq!((i.state().text.as_str(), i.state().syllable), ("한", None));
        i.key(Key::Backspace);
        assert_eq!(i.take(), "");
    }

    #[test]
    fn half_width_types_japanese_as_it_is_until_pressed_again_or_the_language_changes() {
        let mut i = Input::new(Language::Japanese);
        i.key(Key::HalfWidth);
        assert!(i.state().half_width);
        // the JIS keys' characters as they are (not 、。 nor full-width), with spaces
        typed(&mut i, "VRCT 1.5\"@");
        assert_eq!(i.state().text, "VRCT 1.5\"@");
        i.key(Key::HalfWidth);
        assert!(!i.state().half_width);
        i.key(Key::HalfWidth);
        i.set_language(Language::Korean);
        assert!(!i.state().half_width);
        // only Japanese has it
        i.key(Key::HalfWidth);
        assert!(!i.state().half_width);
    }

    fn moved(i: &mut Input, left: bool, word: bool, select: bool) {
        i.key(Key::Move { left, word, select });
    }

    /// text + after, as shown (unlike take, keeps what undo holds)
    fn shown(i: &Input) -> String {
        i.text.clone() + &i.after
    }

    #[test]
    fn a_selection_is_replaced_by_typing_and_deleted_by_backspace() {
        let mut i = Input::new(Language::English);
        typed(&mut i, "hello world");
        moved(&mut i, true, true, true);
        assert_eq!((i.selected_text().as_deref(), i.state().selected), (Some("world"), (0, 5)));
        typed(&mut i, "VR");
        assert_eq!(i.state().text, "hello VR");
        // Shift ◀ selects after the cursor, Shift ▶ before it; ◀ without Shift goes to its start
        i.set_cursor(0);
        moved(&mut i, false, false, true);
        moved(&mut i, false, false, true);
        assert_eq!((i.selected_text().as_deref(), i.state().selected), (Some("he"), (2, 0)));
        i.key(Key::Left);
        assert_eq!((i.state().text.as_str(), i.selected_text()), ("", None));
        i.key(Key::SelectAll);
        i.key(Key::Backspace);
        assert_eq!(shown(&i), "");
    }

    #[test]
    fn ctrl_arrows_move_by_words_of_each_kind_of_character() {
        let mut i = Input::new(Language::English);
        typed(&mut i, "日本語のテキスト  abc.");
        let mut stops = vec![];
        for _ in 0..5 {
            moved(&mut i, true, true, false);
            stops.push(i.state().text.chars().count());
        }
        assert_eq!(stops, [13, 10, 4, 3, 0]);
        moved(&mut i, false, true, false);
        assert_eq!(i.state().text, "日本語");
    }

    #[test]
    fn undo_takes_back_typing_in_a_row_and_each_other_edit() {
        let mut i = Input::new(Language::English);
        typed(&mut i, "ab");
        i.key(Key::Left);
        typed(&mut i, "c");
        assert_eq!(shown(&i), "acb");
        i.key(Key::Undo);
        assert_eq!((i.state().text.as_str(), i.state().after.as_str()), ("a", "b"));
        i.key(Key::Undo);
        assert_eq!(shown(&i), "");
        i.key(Key::Redo);
        i.key(Key::Redo);
        assert_eq!(shown(&i), "acb");
        // a new edit: nothing to redo
        i.key(Key::Undo);
        typed(&mut i, "x");
        i.key(Key::Redo);
        assert_eq!(shown(&i), "axb");
        // clearing is undone too; sending (take) leaves nothing to undo
        i.clear();
        i.key(Key::Undo);
        assert_eq!(shown(&i), "axb");
        i.take();
        i.key(Key::Undo);
        assert_eq!(shown(&i), "");
    }

    #[test]
    fn cut_and_paste_go_through_the_selection() {
        let mut i = Input::new(Language::English);
        typed(&mut i, "one two");
        moved(&mut i, true, true, true);
        i.cut();
        assert_eq!(i.state().text, "one ");
        i.paste("a\r\nb\tc\u{7}");
        assert_eq!(i.state().text, "one a\nb c");
        i.key(Key::SelectAll);
        i.paste("all");
        assert_eq!(shown(&i), "all");
        i.key(Key::Undo);
        assert_eq!(shown(&i), "one a\nb c");
    }

    #[test]
    fn undo_while_a_korean_syllable_is_made_drops_it_only() {
        let mut i = Input::new(Language::Korean);
        typed(&mut i, "gksr");
        i.key(Key::Undo);
        let s = i.state();
        assert_eq!((s.text.as_str(), s.syllable), ("한", None));
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
    fn each_language_sends_its_own_keys_to_rime() {
        // Zhuyin's digits and , . ; / - are its symbols; the others put them in the text
        for c in ['1', '3', ',', '.', ';', '/', '-', 'q'] {
            assert!(Language::Zhuyin.rime_types(c, false), "{c}");
        }
        assert!(!Language::Chinese.rime_types('1', false) && !Language::Cangjie.rime_types(',', false));
        assert!(Language::Japanese.rime_types('-', false) && !Language::Chinese.rime_types('-', false));
        // ' splits pinyin syllables only while composing
        assert!(Language::Chinese.rime_types('\'', true) && !Language::Chinese.rime_types('\'', false));
        assert!(!Language::Cangjie.rime_types('A', true));
        // Zhuyin's comma and full stop with Shift; Cangjie and Quick write Chinese punctuation
        assert_eq!((full_width(Language::Zhuyin, '<'), full_width(Language::Quick, ',')), ('，', '，'));
        for language in [Language::Zhuyin, Language::Cangjie, Language::Quick] {
            assert_eq!(Language::from_code(language.code()), Some(language));
            assert!(language.schema().is_some_and(|s| crate::setup::SCHEMAS.contains(&s)));
        }
    }

    #[test]
    fn japanese_waits_for_the_dictionaries() {
        let mut i = Input::new(Language::Japanese);
        typed(&mut i, "nihongo");
        assert_eq!(i.state(), State::default());
    }
}
