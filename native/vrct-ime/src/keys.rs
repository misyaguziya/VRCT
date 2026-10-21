//! What the keyboard's keys type besides themselves: keys.yaml, the table the VR view prints the
//! keys with too
use serde_yaml::Value;
use std::sync::LazyLock;

static KEYS: LazyLock<Value> = LazyLock::new(|| serde_yaml::from_str(include_str!("../keys.yaml")).expect("keys.yaml"));

/// What `key` types by this table of keys.yaml (["punctuation", "ja"], ["korean"]…), if it is in it
pub fn mapped(table: &[&str], key: char) -> Option<char> {
    let table = table.iter().fold(&*KEYS, |v, name| &v[*name]);
    table[key.to_string().as_str()].as_str()?.chars().next()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_key_types_one_character() {
        for table in [&["punctuation", "ja"][..], &["punctuation", "zh"], &["korean"], &["korean_shift"]] {
            let map = table.iter().fold(&*KEYS, |v, name| &v[*name]).as_mapping().unwrap_or_else(|| panic!("{table:?}"));
            for (key, to) in map {
                let (key, to) = (key.as_str().unwrap(), to.as_str().unwrap());
                assert_eq!((key.chars().count(), to.chars().count()), (1, 1), "{table:?}: {key} {to}");
            }
        }
        assert_eq!(KEYS["korean"].as_mapping().unwrap().len(), 26);
        assert_eq!(mapped(&["punctuation", "zh"], '\\'), Some('、'));
        assert_eq!(mapped(&["korean"], 'y'), Some('ㅛ'));
        assert_eq!(mapped(&["punctuation", "ja"], 'a'), None);
    }
}
