// Copyright (c) 2026 misyaguziya. Licensed for use in VRCT only; see LICENSE.
//! Scripted responses at the HTTP boundary, compiled only for unit tests.
use std::cell::RefCell;
use std::collections::VecDeque;

use reqwest::blocking::{Request, RequestBuilder};

use crate::{Res, Resp};

struct Script {
    responses: VecDeque<Res<Resp>>,
    requests: Vec<Request>,
}

thread_local! {
    static SCRIPT: RefCell<Option<Script>> = const { RefCell::new(None) };
}

pub(crate) fn response(status: u16, body: &str) -> Res<Resp> {
    Ok(Resp {
        status,
        body: body.to_owned(),
    })
}

pub(crate) fn send(builder: &RequestBuilder) -> Option<Res<Resp>> {
    SCRIPT.with_borrow_mut(|slot| {
        let script = slot.as_mut()?;
        script
            .requests
            .push(builder.try_clone().unwrap().build().unwrap());
        Some(
            script
                .responses
                .pop_front()
                .expect("unexpected HTTP request"),
        )
    })
}

pub(crate) fn scripted<T>(responses: Vec<Res<Resp>>, run: impl FnOnce() -> T) -> (T, Vec<Request>) {
    struct Reset;
    impl Drop for Reset {
        fn drop(&mut self) {
            SCRIPT.with_borrow_mut(|slot| *slot = None);
        }
    }
    SCRIPT.with_borrow_mut(|slot| {
        assert!(slot.is_none(), "nested HTTP script");
        *slot = Some(Script {
            responses: responses.into(),
            requests: vec![],
        });
    });
    let _reset = Reset;
    let result = run();
    let script = SCRIPT.with_borrow_mut(|slot| slot.take().unwrap());
    assert!(script.responses.is_empty(), "unused HTTP responses");
    (result, script.requests)
}

pub(crate) fn form(request: &Request) -> std::collections::HashMap<String, String> {
    // Reuse reqwest's URL parser to decode percent-encoded form fields.
    let body = std::str::from_utf8(request.body().unwrap().as_bytes().unwrap()).unwrap();
    let url = reqwest::Url::parse(&format!("http://localhost/?{body}")).unwrap();
    url.query_pairs().into_owned().collect()
}
