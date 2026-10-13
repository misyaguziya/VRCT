//! The error answers (errors.py: ErrorCode, ERROR_METADATA, VRCTError) from native/data/error_codes.json
//! (written by native/reference/export_error_codes.py), and the hooks told of each error code
//! (register_error_report_hook: the telemetry).
use crate::ipc::Reply;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

const ERROR_CODES: &str = include_str!("../../data/error_codes.json");

struct Meta {
    message: String,
    category: String,
    severity: String,
}

fn table() -> &'static HashMap<String, Meta> {
    static TABLE: OnceLock<HashMap<String, Meta>> = OnceLock::new();
    TABLE.get_or_init(|| {
        let v: Value = serde_json::from_str(ERROR_CODES).expect("error_codes.json");
        v["codes"].as_array().unwrap().iter().map(|c| {
            (c["code"].as_str().unwrap().to_string(), Meta {
                message: c["message"].as_str().unwrap().into(),
                category: c["category"].as_str().unwrap().into(),
                severity: c["severity"].as_str().unwrap().into(),
            })
        }).collect()
    })
}

pub fn is_code(code: &str) -> bool {
    table().contains_key(code)
}

/// ERROR_METADATA[code]["message"]
pub fn message(code: &str) -> String {
    table().get(code).map(|m| m.message.clone()).unwrap_or_default()
}

type Hook = Box<dyn Fn(&str) + Send + Sync>;

fn hooks() -> &'static Mutex<Vec<Hook>> {
    static HOOKS: OnceLock<Mutex<Vec<Hook>>> = OnceLock::new();
    HOOKS.get_or_init(|| Mutex::new(Vec::new()))
}

/// register_error_report_hook
pub fn register_hook(hook: impl Fn(&str) + Send + Sync + 'static) {
    hooks().lock().unwrap().push(Box::new(hook));
}

/// report_error_code: the hooks only, no answer
pub fn report(code: &str) {
    for hook in hooks().lock().unwrap().iter() {
        hook(code);
    }
}

/// VRCTError.create_error_response: status 400 with the code's message, category and severity
/// (an unknown code panics: they all come from the table)
pub fn error_response(code: &str, data: Value, details: Option<Value>, custom_message: Option<String>) -> Reply {
    let meta = table().get(code).unwrap_or_else(|| panic!("unknown error code {code}"));
    let reply = Reply {
        status: 400,
        result: json!({
            "error_code": code,
            "message": custom_message.unwrap_or_else(|| meta.message.clone()),
            "data": data,
            "details": details.unwrap_or_else(|| json!({})),
            "category": meta.category,
            "severity": meta.severity,
        }),
    };
    report(code);
    reply
}

/// The usual form: the code and the value to give back
pub fn error(code: &str, data: Value) -> Reply {
    error_response(code, data, None, None)
}

/// create_exception_error_response: "Error: {exception}" with its type
pub fn exception_response(error: &dyn std::fmt::Display, exception_type: &str, data: Value, code: &str) -> Reply {
    error_response(code, data, Some(json!({"exception_type": exception_type})), Some(format!("Error: {error}")))
}
