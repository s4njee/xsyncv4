//! The transfer module root: the sender and receiver engines, the writer both send
//! through, and the helpers they share. The sender is `transfer::sender`, the receiver
//! `transfer::receiver`, the writer `transfer::outbox`, and the itemized output events
//! `transfer::event`.

use std::io;

use xs_wire::Frame;

use crate::protocol::{decode_err, msg_kind};

fn msg_code(frame: &Frame) -> io::Result<Option<i32>> {
    let message = xs_wire::Message::decode(&frame.payload).map_err(decode_err)?;
    if message.kind == msg_kind::FATAL {
        if !message.text.is_empty() {
            eprintln!("xs-rs: {}", message.text);
        }
        return Ok(Some(message.code as i32));
    }
    if message.kind == msg_kind::ERROR && !message.text.is_empty() {
        eprintln!("xs-rs: {}", message.text);
    }
    Ok(None)
}

mod event;
mod file;
mod hardlink;
mod outbox;
mod receiver;
mod sender;

pub use receiver::run_receiver;
pub use sender::run_sender;
