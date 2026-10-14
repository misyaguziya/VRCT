//! HTTP for every external API, on one reqwest client. reqwest's blocking client times out after
//! 30 s by default; here there is no client-wide timeout and each call passes the one the Python
//! code used (None where Python had none).
//!
//! Tests point the client at a local mock server (`Http::redirected`): the scheme, host and port
//! of every URL are replaced, and the original origin goes in the `x-vrct-original-origin` header,
//! so the recorded requests can be compared with the Python ones URL for URL.
use anyhow::{Context, Result};
use reqwest::blocking::{Client, Response};
use reqwest::Method;
use std::time::Duration;

pub const ORIGINAL_ORIGIN_HEADER: &str = "x-vrct-original-origin";

#[derive(Clone)]
pub struct Http {
    client: Client,
    /// For `download`: requests' timeout=(10, 60) is per connect and per read, which only the async
    /// client has (a total timeout would cut a large weight file)
    download_client: reqwest::Client,
    redirect: Option<String>,
}

/// gets each chunk of a download with the Content-Length
pub type OnChunk<'a> = dyn FnMut(&[u8], Option<u64>) -> std::io::Result<()> + 'a;

pub enum DownloadError {
    Status(u16),
    Other(anyhow::Error),
}

impl<E: Into<anyhow::Error>> From<E> for DownloadError {
    fn from(e: E) -> Self {
        DownloadError::Other(e.into())
    }
}

pub enum Body {
    Json(serde_json::Value),
    Bytes(Vec<u8>),
    Multipart(reqwest::blocking::multipart::Form),
}

impl Http {
    pub fn new() -> Result<Self> {
        // GitHub's API refuses requests without a User-Agent (Python's libraries always send one)
        let client = Client::builder()
            .timeout(None::<Duration>)
            .user_agent(concat!("VRCT/", env!("CARGO_PKG_VERSION")))
            .build()?;
        let download_client = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(10))
            .read_timeout(Duration::from_secs(60))
            // each download runs on its own runtime, and a pooled connection dies with the runtime it was made on
            .pool_max_idle_per_host(0)
            .user_agent(concat!("VRCT/", env!("CARGO_PKG_VERSION")))
            .build()?;
        Ok(Self { client, download_client, redirect: None })
    }

    /// Every request goes to `root` (e.g. "http://127.0.0.1:1234") instead.
    pub fn redirected(root: &str) -> Result<Self> {
        Ok(Self { redirect: Some(root.trim_end_matches('/').to_string()), ..Self::new()? })
    }

    /// The URL to request, and the original origin when redirected
    fn target(&self, url: &str) -> Result<(reqwest::Url, Option<String>)> {
        let mut parsed = reqwest::Url::parse(url).with_context(|| format!("bad URL {url}"))?;
        let Some(root) = &self.redirect else { return Ok((parsed, None)) };
        let origin = parsed.origin().ascii_serialization();
        let target = reqwest::Url::parse(root)?;
        parsed.set_scheme(target.scheme()).ok();
        parsed.set_host(target.host_str())?;
        parsed.set_port(target.port()).ok();
        Ok((parsed, Some(origin)))
    }

    pub fn send(&self, method: Method, url: &str, headers: &[(&str, String)], body: Option<Body>,
                timeout: Option<Duration>) -> Result<Response> {
        let (target, origin) = self.target(url)?;
        let mut request = self.client.request(method, target);
        if let Some(origin) = origin {
            request = request.header(ORIGINAL_ORIGIN_HEADER, origin);
        }
        for (name, value) in headers {
            request = request.header(*name, value);
        }
        request = match body {
            None => request,
            Some(Body::Json(v)) => request.header("content-type", "application/json").body(serde_json::to_vec(&v)?),
            Some(Body::Bytes(b)) => request.body(b),
            Some(Body::Multipart(form)) => request.multipart(form),
        };
        if let Some(t) = timeout {
            request = request.timeout(t);
        }
        Ok(request.send()?)
    }

    pub fn get(&self, url: &str, headers: &[(&str, String)], timeout: Option<Duration>) -> Result<Response> {
        self.send(Method::GET, url, headers, None, timeout)
    }

    /// GET `url` and pass the body to `write` chunk by chunk with the Content-Length (requests'
    /// get(stream=True, timeout=(10, 60)) + iter_content). A 4xx/5xx is `DownloadError::Status`.
    pub fn download(&self, url: &str, write: &mut OnChunk)
                    -> std::result::Result<(), DownloadError> {
        let (target, origin) = self.target(url)?;
        let runtime = tokio::runtime::Builder::new_current_thread().enable_all().build()?;
        runtime.block_on(async {
            let mut request = self.download_client.get(target);
            if let Some(origin) = origin {
                request = request.header(ORIGINAL_ORIGIN_HEADER, origin);
            }
            let mut response = request.send().await?;
            let status = response.status();
            if status.is_client_error() || status.is_server_error() {
                return Err(DownloadError::Status(status.as_u16()));
            }
            let length = response.content_length();
            while let Some(chunk) = response.chunk().await? {
                write(&chunk, length)?;
            }
            Ok(())
        })
    }
}
