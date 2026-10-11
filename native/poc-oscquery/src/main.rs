//! PoC 3: what VRCT's models/osc/osc.py does with python-osc + tinyoscquery, through vrchat_osc.
//!
//!     poc-oscquery [advertise ip]     (default: 127.0.0.1, VRCT's default OSC address)
//!
//! - Advertises an OSC + OSCQuery service ("VRCT-PoC") exposing /avatar, so that VRChat finds it
//!   by mDNS and sends avatar parameters to it (VRChat shows the OSCQuery notification).
//! - Prints /avatar/change and /avatar/parameters/MuteSelf as they arrive, and counts the rest.
//! - Every 5 s asks VRChat's own OSCQuery service ("VRChat-Client-*") for MuteSelf, like
//!   getOSCParameterMuteSelf. Nothing is sent to the chatbox.
//!
//! Check both orders: VRChat first then this, and this first then VRChat.
use std::net::IpAddr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;

use vrchat_osc::models::OscRootNode;
use vrchat_osc::rosc::OscPacket;
use vrchat_osc::{ServiceType, VRChatOSC};

const MUTE_SELF: &str = "/avatar/parameters/MuteSelf";

fn print_packet(packet: OscPacket, others: &AtomicU64) {
    match packet {
        OscPacket::Message(msg) if msg.addr == MUTE_SELF || msg.addr == "/avatar/change" => {
            println!("[recv] {} {:?}", msg.addr, msg.args)
        }
        OscPacket::Message(_) => {
            others.fetch_add(1, Ordering::Relaxed);
        }
        OscPacket::Bundle(b) => b.content.into_iter().for_each(|p| print_packet(p, others)),
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let ip: IpAddr = std::env::args().nth(1).as_deref().unwrap_or("127.0.0.1").parse()?;
    let osc = VRChatOSC::new(Some(ip)).await?;
    println!("advertising on {}", osc.get_osc_ip().await);

    osc.on_connect(|service| match service {
        ServiceType::Osc(name, addr) => println!("[found] osc {name} {addr}"),
        ServiceType::OscQuery(name, addr) => println!("[found] oscquery {name} {addr}"),
    })
    .await;

    let others = Arc::new(AtomicU64::new(0));
    let counter = others.clone();
    osc.register("VRCT-PoC", OscRootNode::new().with_avatar(), move |packet| print_packet(packet, &counter))
        .await?;
    println!("registered VRCT-PoC; Ctrl+C to stop");

    let mut tick = tokio::time::interval(Duration::from_secs(5));
    loop {
        tokio::select! {
            _ = tokio::signal::ctrl_c() => break,
            _ = tick.tick() => {
                match osc.get_parameter(MUTE_SELF, "VRChat-Client-*").await {
                    Ok(found) if found.is_empty() => println!("[query] MuteSelf: no VRChat OSCQuery service yet"),
                    Ok(found) => found.iter().for_each(|(name, node)| println!("[query] {name} MuteSelf = {:?}", node.value)),
                    Err(e) => println!("[query] MuteSelf failed: {e}"),
                }
                println!("[recv] other avatar messages so far: {}", others.load(Ordering::Relaxed));
            }
        }
    }
    osc.shutdown().await?;
    Ok(())
}
