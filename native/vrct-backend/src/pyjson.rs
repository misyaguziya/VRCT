//! Python's json.dumps (indent, ensure_ascii), repr() / str() of JSON values, and int() / float()
//! of what the UI sends: the stdout lines, config.json, the process log and the handlers' input as
//! the Python backend treated them. The escapes are built from character codes.
use crate::pyfmt::{repr_float, repr_str};
use serde_json::Value;

const BACKSLASH: char = 92 as char;
const QUOTE: char = 34 as char;

/// The JSON escape of `c` (json.encoder's ESCAPE_DCT), None when it stays as it is
fn escape(c: char, ensure_ascii: bool) -> Option<String> {
    let short = match c as u32 {
        34 => Some(QUOTE),
        92 => Some(BACKSLASH),
        10 => Some('n'),
        13 => Some('r'),
        9 => Some('t'),
        8 => Some('b'),
        12 => Some('f'),
        _ => None,
    };
    if let Some(s) = short {
        return Some(format!("{BACKSLASH}{s}"));
    }
    if (c as u32) >= 0x20 && ((c as u32) < 0x7f || !ensure_ascii) {
        return None;
    }
    let mut units = [0u16; 2];
    Some(c.encode_utf16(&mut units).iter().map(|u| format!("{BACKSLASH}u{u:04x}")).collect())
}

fn string(s: &str, ensure_ascii: bool, out: &mut String) {
    out.push(QUOTE);
    for c in s.chars() {
        match escape(c, ensure_ascii) {
            Some(e) => out.push_str(&e),
            None => out.push(c),
        }
    }
    out.push(QUOTE);
}

struct Writer {
    indent: Option<usize>,
    ensure_ascii: bool,
    out: String,
}

impl Writer {
    /// The separator before an item: ",\n" and the indentation with indent, ", " without
    fn item(&mut self, first: bool, depth: usize) {
        match self.indent {
            Some(n) => {
                if !first {
                    self.out.push(',');
                }
                self.out.push('\n');
                self.out.push_str(&" ".repeat(n * depth));
            }
            None if !first => self.out.push_str(", "),
            None => {}
        }
    }

    fn end(&mut self, depth: usize) {
        if let Some(n) = self.indent {
            self.out.push('\n');
            self.out.push_str(&" ".repeat(n * depth));
        }
    }

    fn write(&mut self, v: &Value, depth: usize) {
        match v {
            Value::Null => self.out.push_str("null"),
            Value::Bool(b) => self.out.push_str(if *b { "true" } else { "false" }),
            Value::Number(n) if n.is_f64() => self.out.push_str(&repr_float(n.as_f64().unwrap())),
            Value::Number(n) => self.out.push_str(&n.to_string()),
            Value::String(s) => string(s, self.ensure_ascii, &mut self.out),
            Value::Array(items) if items.is_empty() => self.out.push_str("[]"),
            Value::Array(items) => {
                self.out.push('[');
                for (i, item) in items.iter().enumerate() {
                    self.item(i == 0, depth + 1);
                    self.write(item, depth + 1);
                }
                self.end(depth);
                self.out.push(']');
            }
            Value::Object(map) if map.is_empty() => self.out.push_str("{}"),
            Value::Object(map) => {
                self.out.push('{');
                for (i, (k, item)) in map.iter().enumerate() {
                    self.item(i == 0, depth + 1);
                    string(k, self.ensure_ascii, &mut self.out);
                    self.out.push_str(": ");
                    self.write(item, depth + 1);
                }
                self.end(depth);
                self.out.push('}');
            }
        }
    }
}

/// json.dumps(value, indent=indent, ensure_ascii=ensure_ascii)
pub fn dumps(value: &Value, indent: Option<usize>, ensure_ascii: bool) -> String {
    let mut w = Writer { indent, ensure_ascii, out: String::new() };
    w.write(value, 0);
    w.out
}

/// json.dump(value, fp, indent=4, ensure_ascii=False): config.json
pub fn dump_config(value: &Value) -> String {
    dumps(value, Some(4), false)
}

/// repr() of the value as the Python object (the process log's str(dict))
pub fn repr(value: &Value) -> String {
    match value {
        Value::Null => "None".into(),
        Value::Bool(b) => if *b { "True" } else { "False" }.into(),
        Value::Number(n) if n.is_f64() => repr_float(n.as_f64().unwrap()),
        Value::Number(n) => n.to_string(),
        Value::String(s) => repr_str(s),
        Value::Array(items) => format!("[{}]", items.iter().map(repr).collect::<Vec<_>>().join(", ")),
        Value::Object(map) => {
            format!("{{{}}}", map.iter().map(|(k, v)| format!("{}: {}", repr_str(k), repr(v))).collect::<Vec<_>>().join(", "))
        }
    }
}

/// str(value): a str as it is, anything else as repr()
pub fn py_str(value: &Value) -> String {
    match value {
        Value::String(s) => s.clone(),
        _ => repr(value),
    }
}

/// A numeric literal as int() / float() read it: surrounding whitespace, a sign, single "_"
/// between digits
fn literal(s: &str) -> Option<String> {
    let s = crate::pyfmt::strip(s);
    let chars: Vec<char> = s.chars().collect();
    let mut out = String::new();
    for (i, &c) in chars.iter().enumerate() {
        if c == '_' {
            let digit = |j: Option<&char>| j.is_some_and(|c| c.is_ascii_hexdigit());
            if !(i > 0 && digit(chars.get(i - 1)) && digit(chars.get(i + 1))) {
                return None;
            }
            continue;
        }
        out.push(c);
    }
    (!out.is_empty()).then_some(out)
}

/// int(value): None where Python raises
pub fn py_int(value: &Value) -> Option<i64> {
    match value {
        Value::Bool(b) => Some(*b as i64),
        Value::Number(n) => n.as_i64().or_else(|| n.as_f64().filter(|x| x.is_finite()).map(|x| x.trunc() as i64)),
        Value::String(s) => {
            let digits = literal(s)?;
            let body = digits.strip_prefix(['+', '-']).unwrap_or(&digits);
            if body.is_empty() || !body.chars().all(|c| c.is_ascii_digit()) {
                return None;
            }
            digits.parse().ok()
        }
        _ => None,
    }
}

/// float(value): None where Python raises
pub fn py_float(value: &Value) -> Option<f64> {
    match value {
        Value::Bool(b) => Some(*b as i64 as f64),
        Value::Number(n) => n.as_f64(),
        Value::String(s) => {
            let text = literal(s)?;
            let lower = text.to_lowercase();
            let body = lower.strip_prefix(['+', '-']).unwrap_or(&lower);
            // Rust also reads "infinity" / "nan" in any case, as Python does; other words are not numbers
            let named = matches!(body, "inf" | "infinity" | "nan");
            if !named && !body.chars().all(|c| c.is_ascii_digit() || matches!(c, '.' | 'e' | '+' | '-')) {
                return None;
            }
            text.parse().ok()
        }
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn indented_like_python() {
        // printed by CPython 3.11: json.dumps(v, indent=4, ensure_ascii=False)
        let v = json!({"a": [1, 2.5, {"b": null}], "c": {}, "d": [], "e": "日本語", "f": true});
        let expected = ["{", "    \"a\": [", "        1,", "        2.5,", "        {", "            \"b\": null", "        }",
                        "    ],", "    \"c\": {},", "    \"d\": [],", "    \"e\": \"日本語\",", "    \"f\": true", "}"].join("\n");
        assert_eq!(dump_config(&v), expected);
        // a control character is escaped even without ensure_ascii; DEL is not
        let s = format!("x{}y{}z", char::from(1u8), char::from(127u8));
        assert_eq!(dumps(&json!(s), None, false), format!("\"x{BACKSLASH}u0001y{}z\"", char::from(127u8)));
    }

    #[test]
    fn repr_like_python() {
        let v = json!({"status": 348, "log": "it's", "data": [1.0, null, true, "a\"b"]});
        assert_eq!(repr(&v), "{'status': 348, 'log': \"it's\", 'data': [1.0, None, True, 'a\"b']}");
        assert_eq!(py_str(&json!("x")), "x");
        assert_eq!(py_str(&Value::Null), "None");
    }

    #[test]
    fn numbers_like_python() {
        // int(): what CPython 3.11 accepts
        for (v, expected) in [(json!(" 80 "), Some(80)), (json!("1_000"), Some(1000)), (json!("+5"), Some(5)), (json!("-5"), Some(-5)),
                              (json!(true), Some(1)), (json!(80.9), Some(80)), (json!(-2.5), Some(-2)), (json!("8.0"), None),
                              (json!("1__0"), None), (json!("_1"), None), (json!(""), None), (json!(null), None), (json!([1]), None)] {
            assert_eq!(py_int(&v), expected, "{v}");
        }
        for (v, expected) in [(json!(" 1.5 "), Some(1.5)), (json!("1e3"), Some(1000.0)), (json!("1_0.5"), Some(10.5)),
                              (json!(false), Some(0.0)), (json!(3), Some(3.0)), (json!("abc"), None), (json!(null), None)] {
            assert_eq!(py_float(&v), expected, "{v}");
        }
        assert!(py_float(&json!("-inf")).is_some_and(|x| x == f64::NEG_INFINITY));
        assert!(py_float(&json!("NaN")).is_some_and(f64::is_nan));
    }
}
