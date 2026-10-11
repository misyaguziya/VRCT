//! OSC with VRChat (models/osc/osc.py): the chatbox messages sent over UDP (python-osc's
//! encoding), and, when the OSC address is this PC, an OSC + OSCQuery service ("VRCT:<time>")
//! that VRChat finds by mDNS and sends MuteSelf / avatar changes to, plus the MuteSelf query to
//! VRChat's own OSCQuery service. The service side is vrchat_osc (it knows VRChat's mDNS quirks).
//!
//! Unlike tinyoscquery, vrchat_osc listens for OSC on every interface (the OSCQuery HTTP server
//! did so in Python too).
use std::net::{IpAddr, Ipv4Addr, SocketAddr, ToSocketAddrs, UdpSocket};
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use vrchat_osc::models::OscRootNode;
use vrchat_osc::rosc::{self, OscMessage, OscPacket, OscType};
use vrchat_osc::VRChatOSC;

pub const MUTE_SELF: &str = "/avatar/parameters/MuteSelf";
pub const AVATAR_CHANGE: &str = "/avatar/change";
const CHATBOX_INPUT: &str = "/chatbox/input";
const CHATBOX_TYPING: &str = "/chatbox/typing";

/// The UDP payload of an OSC message
pub fn encode(addr: &str, args: Vec<OscType>) -> Vec<u8> {
    rosc::encoder::encode(&OscPacket::Message(OscMessage { addr: addr.into(), args })).expect("an OSC message always encodes")
}

/// OSCQuery (receiving) only for this PC: OSCHandler.is_osc_query_enabled
pub fn is_osc_query_enabled(ip: &str) -> bool {
    matches!(ip, "127.0.0.1" | "localhost")
}

/// Sends to VRChat's OSC port (SimpleUDPClient)
pub struct OscSender {
    socket: UdpSocket,
    target: SocketAddr,
}

impl OscSender {
    pub fn new(ip: &str, port: u16) -> std::io::Result<Self> {
        let target = (ip, port).to_socket_addrs()?.next()
            .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::NotFound, format!("no address for {ip}")))?;
        let local: SocketAddr = if target.is_ipv4() { (Ipv4Addr::UNSPECIFIED, 0).into() } else { "[::]:0".parse().unwrap() };
        Ok(Self { socket: UdpSocket::bind(local)?, target })
    }

    /// /chatbox/typing [flag]
    pub fn send_typing(&self, flag: bool) -> std::io::Result<()> {
        self.socket.send_to(&encode(CHATBOX_TYPING, vec![OscType::Bool(flag)]), self.target).map(|_| ())
    }

    /// /chatbox/input [message, True, notification]; nothing for an empty message
    pub fn send_message(&self, message: &str, notification: bool) -> std::io::Result<()> {
        if message.is_empty() {
            return Ok(());
        }
        let args = vec![OscType::String(message.into()), OscType::Bool(true), OscType::Bool(notification)];
        self.socket.send_to(&encode(CHATBOX_INPUT, args), self.target).map(|_| ())
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum OscEvent {
    /// /avatar/parameters/MuteSelf with a boolean
    MuteSelf(bool),
    /// /avatar/change: an avatar loaded (MuteSelf can be asked for now)
    AvatarChange,
}

fn dispatch(packet: OscPacket, on_event: &(dyn Fn(OscEvent) + Send + Sync)) {
    match packet {
        OscPacket::Message(m) if m.addr == MUTE_SELF => {
            if let Some(OscType::Bool(b)) = m.args.first() {
                on_event(OscEvent::MuteSelf(*b));
            }
        }
        OscPacket::Message(m) if m.addr == AVATAR_CHANGE => on_event(OscEvent::AvatarChange),
        OscPacket::Message(_) => {}
        OscPacket::Bundle(b) => b.content.into_iter().for_each(|p| dispatch(p, on_event)),
    }
}

/// The OSC + OSCQuery service (receiveOscParameters / oscServerStop), on its own runtime
pub struct OscReceiver {
    runtime: tokio::runtime::Runtime,
    osc: Arc<VRChatOSC>,
}

impl OscReceiver {
    /// Advertises the service and calls `on_event` (from the OSC receive task: keep it short).
    /// None when OSCQuery is not enabled for `ip`.
    pub fn start(ip: &str, on_event: impl Fn(OscEvent) + Send + Sync + 'static) -> anyhow::Result<Option<Self>> {
        if !is_osc_query_enabled(ip) {
            return Ok(None);
        }
        let runtime = tokio::runtime::Builder::new_multi_thread().worker_threads(1).thread_name("osc").enable_all().build()?;
        let on_event: Arc<dyn Fn(OscEvent) + Send + Sync> = Arc::new(on_event);
        let osc = runtime.block_on(async {
            let osc = VRChatOSC::new(Some(IpAddr::V4(Ipv4Addr::LOCALHOST))).await?;
            // the address space the Python version advertised (READWRITE_VALUE for each filter)
            let root = OscRootNode::new().with_avatar();
            // tinyoscquery's service creation was retried 5 times, a second apart
            let mut last = None;
            for attempt in 0..5 {
                let name = format!("VRCT:{}", SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs());
                let handler = on_event.clone();
                match osc.register(&name, root.clone(), move |packet| dispatch(packet, &*handler)).await {
                    Ok(()) => return Ok(osc),
                    Err(e) => last = Some(e),
                }
                if attempt < 4 {
                    tokio::time::sleep(Duration::from_secs(1)).await;
                }
            }
            Err(anyhow::anyhow!("OSCQuery service: {:?}", last))
        })?;
        Ok(Some(Self { runtime, osc }))
    }

    /// MuteSelf from VRChat's OSCQuery service (getOSCParameterMuteSelf); None when VRChat is not
    /// found or the avatar has not loaded yet (404) or the node has no value
    pub fn mute_self(&self) -> Result<Option<bool>, String> {
        let found = self.runtime.block_on(self.osc.get_parameter(MUTE_SELF, "VRChat-Client-*")).map_err(|e| e.to_string())?;
        let Some((_, node)) = found.into_iter().next() else { return Ok(None) };
        Ok(node.value.and_then(|values| values.into_iter().next()).and_then(|v| match v {
            vrchat_osc::models::OscValue::Bool(b) => Some(b),
            _ => None,
        }))
    }

    /// Withdraws the service (mDNS goodbye) and stops the servers
    pub fn stop(self) {
        let _ = self.runtime.block_on(self.osc.shutdown());
        self.runtime.shutdown_timeout(Duration::from_secs(2));
    }
}
