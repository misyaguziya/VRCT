//! The bits of Python's string formatting that end up in requests and texts: `str.format` with
//! named fields, `repr()` of a str / list of str, `str.strip()`.
use anyhow::{bail, Result};

/// Python's str.isspace() for one character: Rust's White_Space plus U+001C..U+001F.
pub fn isspace(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

/// str.strip()
pub fn strip(s: &str) -> &str {
    s.trim_matches(isspace)
}

/// `template.format(**args)` for plain `{name}` fields and `{{` / `}}`. A name that is not in
/// `args` is an error (KeyError), as are conversions and format specs (not used by VRCT).
pub fn format(template: &str, args: &[(&str, &str)]) -> Result<String> {
    let mut out = String::new();
    let mut chars = template.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '{' if chars.peek() == Some(&'{') => {
                chars.next();
                out.push('{');
            }
            '}' if chars.peek() == Some(&'}') => {
                chars.next();
                out.push('}');
            }
            '{' => {
                let mut name = String::new();
                loop {
                    match chars.next() {
                        Some('}') => break,
                        Some(c) => name.push(c),
                        None => bail!("Single '{{' encountered in format string"),
                    }
                }
                match args.iter().find(|(k, _)| *k == name) {
                    Some((_, v)) => out.push_str(v),
                    None => bail!("KeyError: {name:?}"),
                }
            }
            '}' => bail!("Single '}}' encountered in format string"),
            c => out.push(c),
        }
    }
    Ok(out)
}

/// str.isprintable() for one non-ASCII character.
// ponytail: control / separator / common format characters only, not the full Unicode category
// table; the strings repr'd here are VRCT's own language names.
fn printable(c: char) -> bool {
    !(c.is_control()
        || (c.is_whitespace() && c != ' ')
        || matches!(c, '\u{ad}' | '\u{600}'..='\u{605}' | '\u{61c}' | '\u{6dd}' | '\u{70f}' | '\u{180e}'
            | '\u{200b}'..='\u{200f}' | '\u{202a}'..='\u{202e}' | '\u{2060}'..='\u{2064}' | '\u{2066}'..='\u{206f}'
            | '\u{feff}' | '\u{fff9}'..='\u{fffb}' | '\u{e000}'..='\u{f8ff}'))
}

/// repr(s)
pub fn repr_str(s: &str) -> String {
    let quote = if s.contains('\'') && !s.contains('"') { '"' } else { '\'' };
    let mut out = String::from(quote);
    for c in s.chars() {
        match c {
            c if c == quote || c == '\\' => {
                out.push('\\');
                out.push(c);
            }
            '\t' => out.push_str("\\t"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            c if (c as u32) < 0x20 || c == '\x7f' => out.push_str(&format!("\\x{:02x}", c as u32)),
            c if c.is_ascii() || printable(c) => out.push(c),
            c if (c as u32) <= 0xff => out.push_str(&format!("\\x{:02x}", c as u32)),
            c if (c as u32) <= 0xffff => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push_str(&format!("\\U{:08x}", c as u32)),
        }
    }
    out.push(quote);
    out
}

/// str(list_of_str) / repr(list_of_str)
pub fn repr_list(items: &[String]) -> String {
    format!("[{}]", items.iter().map(|s| repr_str(s)).collect::<Vec<_>>().join(", "))
}

/// repr(float): the shortest digits, in exponent form below 1e-4 and from 1e16
pub fn repr_float(x: f64) -> String {
    if x.is_nan() {
        return "NaN".into();
    }
    if x.is_infinite() {
        return if x > 0.0 { "Infinity" } else { "-Infinity" }.into();
    }
    let sci = format!("{:e}", x.abs());
    let (mantissa, exp) = sci.split_once('e').unwrap();
    let digits: String = mantissa.chars().filter(|c| *c != '.').collect();
    let exp: i32 = exp.parse().unwrap();
    let sign = if x.is_sign_negative() { "-" } else { "" };
    let point = exp + 1; // digits before the decimal point
    let body = if !(-3..=16).contains(&point) {
        let rest = if digits.len() > 1 { format!(".{}", &digits[1..]) } else { String::new() };
        format!("{}{rest}e{}{:02}", &digits[..1], if exp < 0 { '-' } else { '+' }, exp.abs())
    } else if point <= 0 {
        format!("0.{}{digits}", "0".repeat(-point as usize))
    } else if point as usize >= digits.len() {
        format!("{digits}{}.0", "0".repeat(point as usize - digits.len()))
    } else {
        format!("{}.{}", &digits[..point as usize], &digits[point as usize..])
    };
    format!("{sign}{body}")
}

/// json.dumps(value) with the defaults: ", " and ": ", every character from U+007F escaped
pub fn json_dumps(value: &serde_json::Value) -> String {
    crate::pyjson::dumps(value, None, true)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn json_dumps_matches_python() {
        // printed by CPython 3.11: json.dumps(v)
        for (x, expected) in [(0.0, "0.0"), (-0.0, "-0.0"), (1.0, "1.0"), (0.5, "0.5"), (1e16, "1e+16"),
            (9999999999999998.0, "9999999999999998.0"), (1e-5, "1e-05"), (0.0001, "0.0001"), (1.5e-7, "1.5e-07"),
            (123456789.123, "123456789.123"), (1e22, "1e+22"), (2.5e300, "2.5e+300"), (5e-324, "5e-324"),
            (0.1 + 0.2, "0.30000000000000004"), (-1.25e-10, "-1.25e-10"), (100.0, "100.0"),
            (1234567890123456.7, "1234567890123456.8")] {
            assert_eq!(repr_float(x), expected);
        }
        let v: serde_json::Value = serde_json::from_str(
            r#"{"a": "こんにちは\n\"\\ \u0001\u007f\t😀", "b": [1, 2.0, true, null, {}], "c": {"x": []}}"#).unwrap();
        // the \uXXXX escapes are built here so the source stays plain ASCII
        let u = |hex: &str| format!("\\u{hex}");
        let expected = format!(r#"{{"a": "{}{}{}{}{}\n\"\\ {}{}\t{}{}", "b": [1, 2.0, true, null, {{}}], "c": {{"x": []}}}}"#,
            u("3053"), u("3093"), u("306b"), u("3061"), u("306f"), u("0001"), u("007f"), u("d83d"), u("de00"));
        assert_eq!(json_dumps(&v), expected);
    }

    #[test]
    fn like_python() {
        assert_eq!(repr_list(&["a".into(), "Ta'izzi".into(), "x\"y'z".into(), "t\tn\n".into()]),
                   r#"['a', "Ta'izzi", 'x"y\'z', 't\tn\n']"#);
        assert_eq!(format("{a} {{b}} {c}", &[("a", "1"), ("c", "{x}")]).unwrap(), "1 {b} {x}");
        assert!(format("{role}", &[]).is_err());
        assert_eq!(strip("\x1c a \u{3000}"), "a");
    }
}
