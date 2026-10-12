//! The WebSocket server for the OBS browser source (models/websocket/websocket_server.py): what is
//! sent goes to every client. A client must give `?token=...`: WebSocket is not bound by the
//! same-origin policy, so any web page open on this PC could otherwise listen to the transcripts.
//!
//! A client that drops the connection without a close frame (OBS does) only ends its own task
//! (websockets 15 once took the whole server down that way).
use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use std::net::SocketAddr;
use std::sync::mpsc;
use std::time::Duration;
use tokio::sync::{broadcast, watch};
use tokio_tungstenite::tungstenite::handshake::server::{ErrorResponse, Request, Response};
use tokio_tungstenite::tungstenite::{http, Message};

/// How long `stop` waits for the clients to be closed (WebSocketServer.stop joined for 5 s)
const STOP_WAIT: Duration = Duration::from_secs(5);

/// secrets.token_urlsafe(32): 32 random bytes in URL-safe base64 without padding
pub fn new_auth_token() -> String {
    use base64::Engine;
    let mut bytes = [0u8; 32];
    getrandom::getrandom(&mut bytes).expect("the OS random number generator failed");
    base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(bytes)
}

/// parse_qs(query).get("token", [None])[0]: the first non-empty value ('+' is a space)
fn query_token(query: Option<&str>) -> Option<String> {
    form_urlencoded::parse(query?.as_bytes()).find(|(k, v)| k == "token" && !v.is_empty()).map(|(_, v)| v.into_owned())
}

pub struct WebSocketServer {
    addr: SocketAddr,
    messages: broadcast::Sender<String>,
    stop: watch::Sender<bool>,
    done: mpsc::Receiver<()>,
}

impl WebSocketServer {
    /// Listens on host:port (0: any free port) and serves on its own thread. `token`: None accepts
    /// every client (tests).
    pub fn start(host: &str, port: u16, token: Option<String>) -> Result<Self> {
        let listener = std::net::TcpListener::bind((host, port))?;
        listener.set_nonblocking(true)?;
        let addr = listener.local_addr()?;
        let (messages, _) = broadcast::channel(256);
        let (stop, stop_rx) = watch::channel(false);
        let (done_tx, done) = mpsc::channel();
        let runtime = tokio::runtime::Builder::new_current_thread().enable_all().build()?;
        let tx = messages.clone();
        std::thread::Builder::new().name("websocket_server".into()).spawn(move || {
            runtime.block_on(serve(listener, token, tx, stop_rx));
            let _ = done_tx.send(());
        })?;
        Ok(Self { addr, messages, stop, done })
    }

    pub fn port(&self) -> u16 {
        self.addr.port()
    }

    /// To every client connected now
    pub fn send(&self, message: &str) {
        let _ = self.messages.send(message.to_string());
    }

    /// Stops listening and closes the clients
    pub fn stop(self) {
        let _ = self.stop.send(true);
        let _ = self.done.recv_timeout(STOP_WAIT + Duration::from_secs(1));
    }
}

async fn serve(listener: std::net::TcpListener, token: Option<String>, tx: broadcast::Sender<String>,
               mut stop: watch::Receiver<bool>) {
    let Ok(listener) = tokio::net::TcpListener::from_std(listener) else { return };
    let mut clients = tokio::task::JoinSet::new();
    loop {
        tokio::select! {
            accepted = listener.accept() => {
                if let Ok((stream, _)) = accepted {
                    clients.spawn(client(stream, token.clone(), tx.clone(), stop.clone()));
                }
            }
            _ = stop.changed() => break,
        }
    }
    drop(listener);
    let _ = tokio::time::timeout(STOP_WAIT, async { while clients.join_next().await.is_some() {} }).await;
}

async fn client(stream: tokio::net::TcpStream, token: Option<String>, tx: broadcast::Sender<String>,
                mut stop: watch::Receiver<bool>) {
    let check = |request: &Request, response: Response| -> Result<Response, ErrorResponse> {
        match &token {
            Some(t) if query_token(request.uri().query()).as_ref() != Some(t) => Err(http::Response::builder()
                .status(http::StatusCode::FORBIDDEN)
                .header("Content-Type", "text/plain; charset=utf-8")
                .body(Some("Forbidden: invalid or missing token\n".into()))
                .unwrap()),
            _ => Ok(response),
        }
    };
    let Ok(ws) = tokio_tungstenite::accept_hdr_async(stream, check).await else { return };
    let mut messages = tx.subscribe();
    let (mut write, mut read) = ws.split();
    loop {
        tokio::select! {
            incoming = read.next() => match incoming {
                // what clients send is not used (Model.message_handler did nothing)
                Some(Ok(Message::Close(_))) | Some(Err(_)) | None => break,
                Some(Ok(_)) => {}
            },
            message = messages.recv() => match message {
                Ok(text) => if write.send(Message::text(text)).await.is_err() { break },
                Err(broadcast::error::RecvError::Lagged(_)) => {}
                Err(broadcast::error::RecvError::Closed) => break,
            },
            _ = stop.changed() => {
                let _ = write.send(Message::Close(None)).await;
                break;
            }
        }
    }
}
