//! The services that keep state between requests (model.py): the watchdog, OSC with VRChat, the
//! WebSocket and OBS browser source servers.
use crate::config::Config;
use crate::logs;
use crate::obs::{build_overlay_html, ObsServer};
use crate::osc::{self, OscEvent, OscReceiver, OscSender};
use crate::websocket::WebSocketServer;
use anyhow::{anyhow, Result};
use serde_json::Value;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::time::{Duration, Instant};

// ---------------------------------------------------------------------------------- watchdog

/// models/watchdog: the UI feeds it every 20 s; checked every `interval`, a feed older than
/// `timeout` calls the callback (again at each check until it ends the process)
pub struct Watchdog {
    last_feed: Mutex<Instant>,
    started: AtomicBool,
    stopped: Arc<AtomicBool>,
}

impl Default for Watchdog {
    fn default() -> Self {
        Self { last_feed: Mutex::new(Instant::now()), started: AtomicBool::new(false), stopped: Arc::new(AtomicBool::new(false)) }
    }
}

impl Watchdog {
    pub fn feed(&self) {
        *self.last_feed.lock().unwrap() = Instant::now();
    }

    pub fn start(self: &Arc<Self>, timeout: Duration, interval: Duration, on_timeout: impl Fn() + Send + 'static) {
        if self.started.swap(true, Ordering::SeqCst) {
            return;
        }
        self.feed();
        let me = self.clone();
        let _ = std::thread::Builder::new().name("watchdog".into()).spawn(move || {
            while !me.stopped.load(Ordering::SeqCst) {
                if me.last_feed.lock().unwrap().elapsed() > timeout {
                    on_timeout();
                }
                std::thread::sleep(interval);
            }
        });
    }

    /// The thread ends at its next check (a daemon thread in Python too)
    pub fn stop(&self) {
        self.stopped.store(true, Ordering::SeqCst);
    }
}

// ------------------------------------------------------------------------------------ servers

struct Obs {
    host: String,
    port: i64,
    _server: ObsServer,
}

/// The WebSocket server (messages to OBS / VRCT-TTS) and the OBS browser source's HTTP server
#[derive(Default)]
pub struct Servers {
    websocket: Mutex<Option<WebSocketServer>>,
    obs: Mutex<Option<Obs>>,
}

fn port_of(port: i64) -> Result<u16> {
    u16::try_from(port).map_err(|_| anyhow!("port {port} out of range"))
}

impl Servers {
    /// startWebSocketServer: nothing when it runs; a failure is logged and leaves it stopped
    pub fn start_websocket(&self, config: &Config, host: &str, port: i64) {
        let mut ws = self.websocket.lock().unwrap();
        if ws.is_some() {
            return;
        }
        let token = config.get_str("WEBSOCKET_AUTH_TOKEN");
        match port_of(port).and_then(|port| WebSocketServer::start(host, port, Some(token))) {
            Ok(server) => *ws = Some(server),
            Err(e) => logs::error("start WebSocket server", &format!("{e:#}")),
        }
    }

    pub fn stop_websocket(&self) {
        if let Some(server) = self.websocket.lock().unwrap().take() {
            server.stop();
        }
    }

    pub fn websocket_alive(&self) -> bool {
        self.websocket.lock().unwrap().is_some()
    }

    /// websocketSendMessage: json.dumps of the message to every client (nothing when stopped)
    pub fn websocket_send(&self, message: &Value) {
        if let Some(server) = &*self.websocket.lock().unwrap() {
            server.send(&crate::pyjson::dumps(message, None, true));
        }
    }

    /// startObsBrowserSourceServer: kept when it serves host:port already, else started again
    pub fn start_obs(&self, config: &Config, host: &str, port: i64) {
        let mut obs = self.obs.lock().unwrap();
        if obs.as_ref().is_some_and(|o| o.host == host && o.port == port) {
            return;
        }
        *obs = None;
        let token = config.get_str("WEBSOCKET_AUTH_TOKEN");
        let page_config = config.clone();
        let page = move || build_overlay_html(&page_config.serialized(), &token);
        match port_of(port).and_then(|p| ObsServer::start(host, p, page)) {
            Ok(server) => *obs = Some(Obs { host: host.into(), port, _server: server }),
            Err(e) => logs::error("start OBS browser source server", &format!("{e:#}")),
        }
    }

    pub fn stop_obs(&self) {
        // dropped: it stops listening
        self.obs.lock().unwrap().take();
    }

    pub fn obs_alive(&self) -> bool {
        self.obs.lock().unwrap().is_some()
    }
}

// ---------------------------------------------------------------------------------------- OSC

struct OscState {
    ip: String,
    port: i64,
    sender: Option<OscSender>,
    receiver: Option<OscReceiver>,
}

type OscHandler = Arc<dyn Fn(OscEvent) + Send + Sync>;

/// OSCHandler: the chatbox sender, and the OSCQuery service when the address is this PC
pub struct Osc {
    state: Mutex<OscState>,
    on_event: OnceLock<OscHandler>,
}

fn sender(ip: &str, port: i64) -> Result<OscSender> {
    Ok(OscSender::new(ip, port_of(port)?)?)
}

impl Osc {
    pub fn new(ip: &str, port: i64) -> Self {
        let sender = sender(ip, port).map_err(|e| logs::error("OSC sender", &format!("{e:#}"))).ok();
        Self { state: Mutex::new(OscState { ip: ip.into(), port, sender, receiver: None }), on_event: OnceLock::new() }
    }

    fn restart(&self, state: &mut OscState) {
        if let Some(receiver) = state.receiver.take() {
            receiver.stop();
        }
        if let Some(handler) = self.on_event.get().cloned() {
            match OscReceiver::start(&state.ip, move |e| handler(e)) {
                Ok(receiver) => state.receiver = receiver,
                Err(e) => logs::error("OSC receive", &format!("{e:#}")),
            }
        }
    }

    /// setOscIpAddress: the receiver stops, then a sender for the address (an error leaves the old
    /// one), then the receiver starts again for the new address
    pub fn set_ip(&self, ip: &str) -> Result<()> {
        let mut state = self.state.lock().unwrap();
        if let Some(receiver) = state.receiver.take() {
            receiver.stop();
        }
        state.ip = ip.into();
        state.sender = Some(sender(ip, state.port)?);
        self.restart(&mut state);
        Ok(())
    }

    pub fn set_port(&self, port: i64) -> Result<()> {
        let mut state = self.state.lock().unwrap();
        if let Some(receiver) = state.receiver.take() {
            receiver.stop();
        }
        state.port = port;
        state.sender = Some(sender(&state.ip, port)?);
        self.restart(&mut state);
        Ok(())
    }

    /// startReceiveOSC: the events go to `on_event` from now on
    pub fn start_receive(&self, on_event: impl Fn(OscEvent) + Send + Sync + 'static) {
        let _ = self.on_event.set(Arc::new(on_event));
        let mut state = self.state.lock().unwrap();
        self.restart(&mut state);
    }

    pub fn stop_receive(&self) {
        if let Some(receiver) = self.state.lock().unwrap().receiver.take() {
            receiver.stop();
        }
    }

    pub fn is_osc_query_enabled(&self) -> bool {
        osc::is_osc_query_enabled(&self.state.lock().unwrap().ip)
    }

    fn with_sender(&self, send: impl FnOnce(&OscSender) -> std::io::Result<()>) -> Result<()> {
        let state = self.state.lock().unwrap();
        let sender = state.sender.as_ref().ok_or_else(|| anyhow!("no OSC sender for {}", state.ip))?;
        Ok(send(sender)?)
    }

    pub fn send_typing(&self, flag: bool) -> Result<()> {
        self.with_sender(|s| s.send_typing(flag))
    }

    pub fn send_message(&self, message: &str, notification: bool) -> Result<()> {
        self.with_sender(|s| s.send_message(message, notification))
    }

    /// getOSCParameterMuteSelf: None when VRChat or the avatar's parameter is not there
    pub fn mute_self(&self) -> Option<bool> {
        let state = self.state.lock().unwrap();
        state.receiver.as_ref()?.mute_self(&|l| crate::ipc::log(l)).unwrap_or_else(|e| {
            logs::error("OSC MuteSelf", &e);
            None
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;

    const TIMEOUT: Duration = Duration::from_millis(150);
    const INTERVAL: Duration = Duration::from_millis(20);

    fn counted(dog: &Arc<Watchdog>) -> Arc<AtomicUsize> {
        let calls = Arc::new(AtomicUsize::new(0));
        let c = calls.clone();
        dog.start(TIMEOUT, INTERVAL, move || {
            c.fetch_add(1, Ordering::SeqCst);
        });
        calls
    }

    #[test]
    fn a_fed_watchdog_stays_quiet_and_a_hungry_one_calls() {
        let dog = Arc::new(Watchdog::default());
        let calls = counted(&dog);
        for _ in 0..10 {
            std::thread::sleep(Duration::from_millis(50));
            dog.feed();
        }
        assert_eq!(calls.load(Ordering::SeqCst), 0);
        std::thread::sleep(TIMEOUT * 3);
        // every check after the timeout calls (main.rs's escalate runs once)
        assert!(calls.load(Ordering::SeqCst) >= 2);
        dog.stop();
    }

    #[test]
    fn starting_twice_watches_once_and_stop_ends_it() {
        let dog = Arc::new(Watchdog::default());
        let first = counted(&dog);
        let second = counted(&dog);
        std::thread::sleep(TIMEOUT * 2);
        assert!(first.load(Ordering::SeqCst) >= 1);
        assert_eq!(second.load(Ordering::SeqCst), 0);
        dog.stop();
        std::thread::sleep(INTERVAL * 3);
        let after_stop = first.load(Ordering::SeqCst);
        std::thread::sleep(INTERVAL * 5);
        assert_eq!(first.load(Ordering::SeqCst), after_stop);
    }
}
