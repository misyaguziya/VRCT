//! The WebSocket server (B level): the token check, delivery to every client, a client that drops
//! the connection without a close frame (the OBS browser source), and stop.
use std::net::TcpStream;
use std::time::Duration;
use tokio_tungstenite::tungstenite::stream::MaybeTlsStream;
use tokio_tungstenite::tungstenite::{self, Message, WebSocket};
use vrct_backend::websocket::{new_auth_token, WebSocketServer};

type Client = WebSocket<MaybeTlsStream<TcpStream>>;

fn connect(port: u16, query: &str) -> Result<Client, tungstenite::Error> {
    let (ws, _) = tungstenite::connect(format!("ws://127.0.0.1:{port}/{query}"))?;
    if let MaybeTlsStream::Plain(s) = ws.get_ref() {
        s.set_read_timeout(Some(Duration::from_secs(5))).unwrap();
    }
    Ok(ws)
}

fn next_text(ws: &mut Client) -> String {
    match ws.read().unwrap() {
        Message::Text(t) => t.to_string(),
        other => panic!("{other:?}"),
    }
}

/// The server subscribes a client once its handshake is done; give it that moment
fn settle() {
    std::thread::sleep(Duration::from_millis(100));
}

#[test]
fn token_is_required() {
    let token = new_auth_token();
    assert_eq!(token.len(), 43);
    assert!(token.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_'));
    let server = WebSocketServer::start("127.0.0.1", 0, Some(token.clone())).unwrap();
    for query in ["".to_string(), "?token=".into(), "?token=wrong".into(), format!("?tok={token}")] {
        match connect(server.port(), &query) {
            Err(tungstenite::Error::Http(response)) => {
                assert_eq!(response.status(), 403, "{query}");
                assert_eq!(response.body().as_deref(), Some(&b"Forbidden: invalid or missing token\n"[..]));
            }
            other => panic!("{query}: {:?}", other.map(|_| ())),
        }
    }
    let encoded: String = token.bytes().map(|b| format!("%{b:02X}")).collect();
    for query in [format!("?token={token}"), format!("?a=1&token={encoded}&token=x"), format!("x/y?token={token}")] {
        connect(server.port(), &query).unwrap_or_else(|e| panic!("{query}: {e}"));
    }
    server.stop();

    let open = WebSocketServer::start("127.0.0.1", 0, None).unwrap();
    connect(open.port(), "").unwrap();
    open.stop();
}

#[test]
fn every_client_gets_messages_and_survives_a_dropped_client() {
    let server = WebSocketServer::start("127.0.0.1", 0, Some("t".into())).unwrap();
    let (mut a, mut b) = (connect(server.port(), "?token=t").unwrap(), connect(server.port(), "?token=t").unwrap());
    let dropped = connect(server.port(), "?token=t").unwrap();
    settle();
    server.send(r#"{"type": "SENT", "message": "こ"}"#);
    assert_eq!(next_text(&mut a), r#"{"type": "SENT", "message": "こ"}"#);
    assert_eq!(next_text(&mut b), r#"{"type": "SENT", "message": "こ"}"#);

    // gone without a close frame, as OBS does when the source is hidden or removed
    drop(dropped);
    settle();
    server.send("after drop");
    assert_eq!(next_text(&mut a), "after drop");
    let mut c = connect(server.port(), "?token=t").unwrap();
    settle();
    server.send("new client");
    assert_eq!(next_text(&mut c), "new client");
    assert_eq!(next_text(&mut b), "after drop");
    assert_eq!(next_text(&mut b), "new client");
    assert_eq!(next_text(&mut a), "new client");

    // a client's own messages are ignored, pings are answered
    a.send(Message::text("hello")).unwrap();
    a.send(Message::Ping(vec![1, 2])).unwrap();
    let pong = a.read().unwrap();
    assert!(matches!(&pong, Message::Pong(p) if p[..] == [1, 2]), "{pong:?}");

    let port = server.port();
    server.stop();
    assert!(matches!(a.read(), Ok(Message::Close(_)) | Err(_)));
    // the port is free again
    WebSocketServer::start("127.0.0.1", port, None).unwrap().stop();
}
