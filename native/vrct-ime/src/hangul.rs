//! Korean input: the 2-set (dubeolsik) layout on QWERTY, composing jamo into syllables. No
//! dictionary is needed (Hanja is not offered).

/// The jamo a key types (Shift gives the tense consonants and ㅒ ㅖ)
pub fn jamo_of_key(key: char) -> Option<char> {
    const LOWER: &str = "qwertyuiopasdfghjklzxcvbnm";
    const JAMO: &str = "ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔㅁㄴㅇㄹㅎㅗㅓㅏㅣㅋㅌㅊㅍㅠㅜㅡ";
    let shifted = match key {
        'Q' => Some('ㅃ'),
        'W' => Some('ㅉ'),
        'E' => Some('ㄸ'),
        'R' => Some('ㄲ'),
        'T' => Some('ㅆ'),
        'O' => Some('ㅒ'),
        'P' => Some('ㅖ'),
        _ => None,
    };
    shifted.or_else(|| {
        let lower = key.to_ascii_lowercase();
        LOWER.chars().position(|c| c == lower).and_then(|i| JAMO.chars().nth(i))
    })
}

const INITIALS: [char; 19] = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const MEDIALS: [char; 21] = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'];
/// index 0: no final
const FINALS: [char; 28] = ['\0', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
                            'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const VOWEL_PAIRS: [(char, char, char); 7] =
    [('ㅗ', 'ㅏ', 'ㅘ'), ('ㅗ', 'ㅐ', 'ㅙ'), ('ㅗ', 'ㅣ', 'ㅚ'), ('ㅜ', 'ㅓ', 'ㅝ'), ('ㅜ', 'ㅔ', 'ㅞ'), ('ㅜ', 'ㅣ', 'ㅟ'), ('ㅡ', 'ㅣ', 'ㅢ')];
const FINAL_PAIRS: [(char, char, char); 11] = [('ㄱ', 'ㅅ', 'ㄳ'), ('ㄴ', 'ㅈ', 'ㄵ'), ('ㄴ', 'ㅎ', 'ㄶ'), ('ㄹ', 'ㄱ', 'ㄺ'), ('ㄹ', 'ㅁ', 'ㄻ'),
                                               ('ㄹ', 'ㅂ', 'ㄼ'), ('ㄹ', 'ㅅ', 'ㄽ'), ('ㄹ', 'ㅌ', 'ㄾ'), ('ㄹ', 'ㅍ', 'ㄿ'), ('ㄹ', 'ㅎ', 'ㅀ'), ('ㅂ', 'ㅅ', 'ㅄ')];

fn is_vowel(c: char) -> bool {
    MEDIALS.contains(&c)
}

fn pair(pairs: &[(char, char, char)], a: char, b: char) -> Option<char> {
    pairs.iter().find(|p| p.0 == a && p.1 == b).map(|p| p.2)
}

fn split(pairs: &[(char, char, char)], c: char) -> Option<(char, char)> {
    pairs.iter().find(|p| p.2 == c).map(|p| (p.0, p.1))
}

/// The syllable being composed: its initial, medial and final jamo
#[derive(Clone, Copy, Debug, Default, PartialEq)]
struct Syllable {
    initial: Option<char>,
    medial: Option<char>,
    last: Option<char>,
}

impl Syllable {
    fn is_empty(&self) -> bool {
        self.initial.is_none() && self.medial.is_none()
    }

    /// The precomposed syllable, or the lone jamo while it is not one yet
    fn text(&self) -> String {
        let index = |list: &[char], c: char| list.iter().position(|x| *x == c).unwrap() as u32;
        match (self.initial, self.medial, self.last) {
            (Some(i), Some(m), last) => {
                let code = 0xAC00 + (index(&INITIALS, i) * 21 + index(&MEDIALS, m)) * 28 + last.map_or(0, |f| index(&FINALS, f));
                char::from_u32(code).map(String::from).unwrap_or_default()
            }
            (Some(i), None, _) => i.to_string(),
            (None, Some(m), _) => m.to_string(),
            (None, None, _) => String::new(),
        }
    }

    /// The jamo it is made of (what the keyboard shows while composing)
    fn parts(&self) -> Vec<char> {
        let mut parts = vec![];
        parts.extend(self.initial);
        if let Some(m) = self.medial {
            match split(&VOWEL_PAIRS, m) {
                Some((a, b)) => parts.extend([a, b]),
                None => parts.push(m),
            }
        }
        if let Some(f) = self.last {
            match split(&FINAL_PAIRS, f) {
                Some((a, b)) => parts.extend([a, b]),
                None => parts.push(f),
            }
        }
        parts
    }
}

/// Composes jamo into Hangul: `text` is what is done, the syllable being made shows after it
#[derive(Default)]
pub struct Composer {
    text: String,
    current: Syllable,
    /// the states of the current syllable before each jamo (for backspace)
    history: Vec<Syllable>,
}

impl Composer {
    pub fn new() -> Self {
        Self::default()
    }

    /// The syllables done (the one being composed not included)
    pub fn written(&self) -> &str {
        &self.text
    }

    /// The text so far, the syllable being composed included
    pub fn preedit(&self) -> String {
        self.text.clone() + &self.current.text()
    }

    /// The syllable being composed and its jamo (None when nothing is being composed)
    pub fn composing(&self) -> Option<(String, Vec<char>)> {
        (!self.current.is_empty()).then(|| (self.current.text(), self.current.parts()))
    }

    fn finish(&mut self) {
        self.text += &self.current.text();
        self.current = Syllable::default();
        self.history.clear();
    }

    fn start(&mut self, s: Syllable) {
        self.finish();
        self.history.push(Syllable::default());
        self.current = s;
    }

    /// A jamo (a key's) or any other character (it ends the syllable and goes in as it is)
    pub fn input(&mut self, c: char) {
        if INITIALS.contains(&c) || FINALS[1..].contains(&c) {
            self.consonant(c);
        } else if is_vowel(c) {
            self.vowel(c);
        } else {
            self.finish();
            self.text.push(c);
        }
    }

    fn consonant(&mut self, c: char) {
        let s = self.current;
        let next = match (s.initial, s.medial, s.last) {
            // a final, or a double final
            (Some(_), Some(_), None) if FINALS[1..].contains(&c) => Some(Syllable { last: Some(c), ..s }),
            (Some(_), Some(_), Some(f)) => pair(&FINAL_PAIRS, f, c).map(|d| Syllable { last: Some(d), ..s }),
            _ => None,
        };
        match next {
            Some(next) => {
                self.history.push(s);
                self.current = next;
            }
            None if INITIALS.contains(&c) => self.start(Syllable { initial: Some(c), ..Default::default() }),
            // a double final alone (ㄳ ...) begins no syllable: it goes in as it is
            None => {
                self.finish();
                self.text.push(c);
            }
        }
    }

    fn vowel(&mut self, v: char) {
        let s = self.current;
        match (s.initial, s.medial, s.last) {
            (Some(_), None, _) => {
                self.history.push(s);
                self.current.medial = Some(v);
            }
            (_, Some(m), None) if pair(&VOWEL_PAIRS, m, v).is_some() => {
                self.history.push(s);
                self.current.medial = pair(&VOWEL_PAIRS, m, v);
            }
            // the final moves on to start the next syllable (닭 + ㅏ = 달가)
            (Some(_), Some(_), Some(f)) => {
                let (kept, moved) = match split(&FINAL_PAIRS, f) {
                    Some((a, b)) => (Some(a), b),
                    None => (None, f),
                };
                self.current.last = kept;
                self.finish();
                self.history.push(Syllable::default());
                self.history.push(Syllable { initial: Some(moved), ..Default::default() });
                self.current = Syllable { initial: Some(moved), medial: Some(v), last: None };
            }
            _ => self.start(Syllable { medial: Some(v), ..Default::default() }),
        }
    }

    /// One step back: the last jamo of the syllable, else the last character. False when empty.
    pub fn backspace(&mut self) -> bool {
        if let Some(previous) = self.history.pop() {
            self.current = previous;
            return true;
        }
        self.text.pop().is_some()
    }

    /// Everything as it is, then empty
    pub fn take(&mut self) -> String {
        self.finish();
        std::mem::take(&mut self.text)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn typed(keys: &str) -> Composer {
        let mut c = Composer::new();
        for k in keys.chars() {
            c.input(jamo_of_key(k).unwrap_or(k));
        }
        c
    }

    #[test]
    fn words_on_the_2_set_layout() {
        assert_eq!(typed("dkssudgktpdy").preedit(), "안녕하세요");
        assert_eq!(typed("gksrmf").preedit(), "한글");
        assert_eq!(typed("rkatkgkqslek").preedit(), "감사합니다");
        // a double final, then a vowel takes its second half (닭 + ㅏ = 달가)
        assert_eq!(typed("ekfr").preedit(), "닭");
        assert_eq!(typed("ekfrk").preedit(), "달가");
        // compound vowels; tense consonants with Shift
        assert_eq!(typed("dhkd").preedit(), "왕");
        assert_eq!(typed("dmlwk").preedit(), "의자");
        assert_eq!(typed("Tkd").preedit(), "쌍");
        // ㄸ cannot be a final: it starts the next syllable
        assert_eq!(typed("dkE").preedit(), "아ㄸ");
    }

    #[test]
    fn the_syllable_being_composed_and_its_jamo() {
        let c = typed("dkssudgktpd");
        assert_eq!(c.composing(), Some(("셍".to_string(), vec!['ㅅ', 'ㅔ', 'ㅇ'])));
        let c = typed("dhk");
        assert_eq!(c.composing(), Some(("와".to_string(), vec!['ㅇ', 'ㅗ', 'ㅏ'])));
        assert_eq!(Composer::new().composing(), None);
    }

    #[test]
    fn backspace_takes_back_one_jamo_then_whole_characters() {
        let mut c = typed("gksrmf");
        assert!(c.backspace());
        assert_eq!(c.preedit(), "한그");
        assert!(c.backspace());
        assert_eq!(c.preedit(), "한ㄱ");
        assert!(c.backspace());
        assert_eq!(c.preedit(), "한");
        assert!(c.backspace());
        assert_eq!(c.preedit(), "");
        assert!(!c.backspace());
    }

    #[test]
    fn a_double_final_alone_is_not_an_initial() {
        let mut c = Composer::new();
        c.input('ㄳ');
        c.input('ㅏ');
        assert_eq!(c.take(), "ㄳㅏ");
    }

    #[test]
    fn other_characters_end_the_syllable_and_take_empties() {
        let mut c = typed("dkssud");
        c.input(' ');
        c.input('?');
        assert_eq!(c.preedit(), "안녕 ?");
        assert_eq!(c.take(), "안녕 ?");
        assert_eq!(c.preedit(), "");
    }
}
