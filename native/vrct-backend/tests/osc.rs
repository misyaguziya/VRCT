//! What VRCT sends to VRChat's chatbox against python-osc (native/testdata/osc/osc.json, written by
//! native/reference/export_osc.py): the encoding, and the datagrams OscSender puts on the wire.
use serde_json::Value;
use std::net::UdpSocket;
use std::time::Duration;
use vrct_backend::osc::OscSender;

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

#[test]
fn chatbox_datagrams_match_python_osc() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/osc/osc.json");
    let cases: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    // stands in for VRChat's OSC port
    let vrchat = UdpSocket::bind("127.0.0.1:0").unwrap();
    vrchat.set_read_timeout(Some(Duration::from_secs(5))).unwrap();
    let sender = OscSender::new("127.0.0.1", vrchat.local_addr().unwrap().port()).unwrap();
    let mut buf = [0u8; 2048];
    for case in cases.as_array().unwrap() {
        match case["kind"].as_str().unwrap() {
            "typing" => sender.send_typing(case["flag"].as_bool().unwrap()).unwrap(),
            _ => sender.send_message(case["message"].as_str().unwrap(), case["notification"].as_bool().unwrap()).unwrap(),
        }
        let n = vrchat.recv(&mut buf).unwrap();
        assert_eq!(hex(&buf[..n]), case["bytes"].as_str().unwrap(), "{case}");
    }
    // an empty message is not sent
    sender.send_message("", true).unwrap();
    vrchat.set_read_timeout(Some(Duration::from_millis(200))).unwrap();
    assert!(vrchat.recv(&mut buf).is_err());
}
