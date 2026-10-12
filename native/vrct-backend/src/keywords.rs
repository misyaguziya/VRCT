//! The microphone's word filter (flashtext 2.7's KeywordProcessor, case-insensitive): a keyword
//! matches where it starts and ends at a word boundary, a word being a run of [A-Za-z0-9_]. Any
//! other character (Japanese too) is a boundary, so "テスト" is found inside "これはテストです"
//! while "test" is not found inside "atest".
use std::collections::HashMap;

#[derive(Default)]
struct Node {
    next: HashMap<char, Node>,
    /// a keyword ends here (its clean name; flashtext's `_keyword_` entry)
    keyword: Option<String>,
}

#[derive(Default)]
pub struct Keywords {
    root: Node,
}

fn in_word(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '_'
}

impl Keywords {
    /// add_keyword(keyword): found case-insensitively, reported as written; an empty one is ignored
    pub fn add(&mut self, keyword: &str) {
        if keyword.is_empty() {
            return;
        }
        let mut node = &mut self.root;
        for c in keyword.to_lowercase().chars() {
            node = node.next.entry(c).or_default();
        }
        node.keyword = Some(keyword.to_string());
    }

    /// extract_keywords(sentence): the clean names found, in order
    pub fn extract(&self, sentence: &str) -> Vec<String> {
        let s: Vec<char> = sentence.to_lowercase().chars().collect();
        let mut found = vec![];
        let mut current = &self.root;
        let mut idx = 0;
        while idx < s.len() {
            let c = s[idx];
            if !in_word(c) {
                if current.keyword.is_some() || current.next.contains_key(&c) {
                    let mut longest = current.keyword.clone();
                    if let Some(mut continued) = current.next.get(&c) {
                        let mut idy = idx + 1;
                        let mut end = None;
                        let mut exhausted = true;
                        while idy < s.len() {
                            let inner = s[idy];
                            if !in_word(inner) && continued.keyword.is_some() {
                                longest = continued.keyword.clone();
                                end = Some(idy);
                            }
                            match continued.next.get(&inner) {
                                Some(n) => continued = n,
                                None => {
                                    exhausted = false;
                                    break;
                                }
                            }
                            idy += 1;
                        }
                        if exhausted && continued.keyword.is_some() {
                            longest = continued.keyword.clone();
                            end = Some(idy);
                        }
                        if let Some(end) = end {
                            idx = end;
                        }
                    }
                    found.extend(longest);
                }
                current = &self.root;
            } else if let Some(n) = current.next.get(&c) {
                current = n;
            } else {
                current = &self.root;
                let mut idy = idx + 1;
                while idy < s.len() && in_word(s[idy]) {
                    idy += 1;
                }
                idx = idy;
            }
            if idx + 1 >= s.len() {
                if let Some(k) = &current.keyword {
                    found.push(k.clone());
                }
            }
            idx += 1;
        }
        found
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn kp(words: &[&str]) -> Keywords {
        let mut k = Keywords::default();
        words.iter().for_each(|w| k.add(w));
        k
    }

    // the expected lists are flashtext 2.7's KeywordProcessor().extract_keywords
    #[test]
    fn matches_flashtext() {
        let k = kp(&["test", "テスト", "New York"]);
        assert_eq!(k.extract("これはテストです"), ["テスト"]);
        assert_eq!(k.extract("atest"), Vec::<String>::new());
        assert_eq!(k.extract("a TEST."), ["test"]);
        assert_eq!(k.extract("test"), ["test"]);
        assert_eq!(k.extract("I love new york!"), ["New York"]);
        assert_eq!(k.extract("testing"), Vec::<String>::new());
        assert_eq!(k.extract("テスト"), ["テスト"]);
        assert_eq!(kp(&["a", "a b"]).extract("a b c"), ["a b"]);
        assert_eq!(kp(&[""]).extract("hello"), Vec::<String>::new());
    }
}
