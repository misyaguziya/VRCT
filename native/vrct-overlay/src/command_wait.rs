//! Commands wake an active overlay independently of its high resolution frame timer.
use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle};
use std::sync::{Arc, atomic::{AtomicBool, Ordering}, mpsc};
use std::time::{Duration, Instant};
use windows_sys::Win32::Foundation::{HANDLE, WAIT_OBJECT_0, WAIT_TIMEOUT};
use windows_sys::Win32::System::Threading::{CreateEventW, CreateWaitableTimerExW, SetEvent,
    SetWaitableTimerEx, WaitForMultipleObjects, CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, TIMER_ALL_ACCESS};

struct Notification {
    event: OwnedHandle,
    failed: AtomicBool,
}
impl Notification {
    fn signal(&self) {
        // The Arc keeps the event alive throughout both send and wait.
        if unsafe { SetEvent(self.event.as_raw_handle() as HANDLE) } == 0 {
            self.failed.store(true, Ordering::Relaxed);
        }
    }
}

// Deliberately not Clone: dropping the only sender must notify disconnection.
pub(crate) struct Sender<T> {
    queue: Option<mpsc::Sender<T>>,
    notification: Option<Arc<Notification>>,
}
pub(crate) struct Receiver<T> {
    queue: mpsc::Receiver<T>,
    notification: Option<Arc<Notification>>,
    timer: Option<OwnedHandle>,
    initialized: bool,
    disabled: bool,
}
pub(crate) fn channel<T>() -> (Sender<T>, Receiver<T>) {
    let (tx, rx) = mpsc::channel();
    let event = unsafe { CreateEventW(std::ptr::null(), 0, 0, std::ptr::null()) };
    let notification = (!event.is_null()).then(|| Arc::new(Notification {
        // CreateEventW returned a unique owned handle; it is closed only after both ends drop.
        event: unsafe { OwnedHandle::from_raw_handle(event) }, failed: AtomicBool::new(false),
    }));
    (Sender { queue: Some(tx), notification: notification.clone() },
     Receiver { queue: rx, notification, timer: None, initialized: false, disabled: false })
}
impl<T> Sender<T> {
    pub(crate) fn send(&self, value: T) -> Result<(), mpsc::SendError<T>> {
        self.queue.as_ref().unwrap().send(value)?;
        if let Some(notification) = &self.notification { notification.signal(); }
        Ok(())
    }
}
impl<T> Drop for Sender<T> {
    fn drop(&mut self) {
        // Publish disconnection before waking the receiver (including an otherwise empty queue).
        drop(self.queue.take());
        if let Some(notification) = &self.notification { notification.signal(); }
    }
}
fn relative_due_time(duration: Duration) -> i64 {
    -(duration.as_nanos().div_ceil(100).clamp(1, i64::MAX as u128) as i64)
}
fn watchdog_ms(duration: Duration) -> u32 {
    duration.as_millis().saturating_add(101).min((u32::MAX - 1) as u128) as u32
}
impl<T> Receiver<T> {
    pub(crate) fn try_recv(&self) -> Result<T, mpsc::TryRecvError> { self.queue.try_recv() }

    fn disable(&mut self, log: &dyn Fn(String), reason: &str) {
        if !self.disabled { log(format!("overlay wait: recv_timeout fallback ({reason})")); }
        self.disabled = true;
        self.timer = None;
    }

    pub(crate) fn recv_timeout(&mut self, duration: Duration, precise: bool, log: &dyn Fn(String))
        -> Result<T, mpsc::RecvTimeoutError>
    {
        let deadline = Instant::now() + duration;
        if !precise { return self.queue.recv_timeout(duration); }
        loop {
            // Queue first: zero-duration waits still drain pending commands, including Stop.
            match self.queue.try_recv() {
                Ok(value) => return Ok(value),
                Err(mpsc::TryRecvError::Disconnected) => return Err(mpsc::RecvTimeoutError::Disconnected),
                Err(mpsc::TryRecvError::Empty) => {}
            }
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() { return Err(mpsc::RecvTimeoutError::Timeout); }
            if !self.initialized {
                self.initialized = true;
                if self.notification.is_some() {
                    let timer = unsafe { CreateWaitableTimerExW(std::ptr::null(), std::ptr::null(),
                        CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, TIMER_ALL_ACCESS) };
                    if !timer.is_null() {
                        self.timer = Some(unsafe { OwnedHandle::from_raw_handle(timer) });
                        log("overlay wait: high-resolution waitable timer".into());
                    } else { self.disable(log, "timer creation failed"); }
                } else { self.disable(log, "event creation failed"); }
            }
            if self.notification.as_ref().is_some_and(|n| n.failed.load(Ordering::Relaxed)) {
                self.disable(log, "command notification failed");
            }
            if self.disabled {
                return self.queue.recv_timeout(deadline.saturating_duration_since(Instant::now()));
            }
            let timer = self.timer.as_ref().unwrap().as_raw_handle() as HANDLE;
            let due = relative_due_time(deadline.saturating_duration_since(Instant::now()));
            if unsafe { SetWaitableTimerEx(timer, &due, 0, None, std::ptr::null(), std::ptr::null(), 0) } == 0 {
                self.disable(log, "timer arming failed");
                continue;
            }
            let handles = [self.notification.as_ref().unwrap().event.as_raw_handle() as HANDLE, timer];
            // Finite watchdog also bounds a failed notification/timer; never spin or change
            // the process-wide timer resolution. Receiver owns timer until this wait returns.
            let result = unsafe { WaitForMultipleObjects(2, handles.as_ptr(), 0, watchdog_ms(remaining)) };
            if result != WAIT_OBJECT_0 && result != WAIT_OBJECT_0 + 1 {
                self.disable(log, if result == WAIT_TIMEOUT { "wait watchdog expired" } else { "wait failed" });
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn receive<T>(rx: &mut Receiver<T>, duration: Duration) -> Result<T, mpsc::RecvTimeoutError> {
        rx.recv_timeout(duration, true, &|_| {})
    }
    #[test]
    fn prequeued_commands_and_zero_timeout() {
        let (tx, mut rx) = channel();
        tx.send(1).unwrap(); tx.send(2).unwrap();
        assert_eq!(receive(&mut rx, Duration::ZERO), Ok(1));
        assert_eq!(receive(&mut rx, Duration::ZERO), Ok(2));
        assert_eq!(receive(&mut rx, Duration::ZERO), Err(mpsc::RecvTimeoutError::Timeout));
        drop(tx);
        assert_eq!(receive(&mut rx, Duration::ZERO), Err(mpsc::RecvTimeoutError::Disconnected));
    }
    #[test]
    fn commands_and_disconnect_wake_waiter() {
      for precise in [false, true] {
        for disconnect in [false, true] {
            let (tx, mut rx) = channel();
            let (ready, wait) = mpsc::channel();
            let (done, completion) = mpsc::channel();
            let thread = std::thread::spawn(move || {
                ready.send(()).unwrap();
                let result = rx.recv_timeout(Duration::from_secs(5), precise, &|_| {});
                done.send(result).unwrap();
            });
            wait.recv().unwrap();
            // Allow entry to the wait; correctness does not depend on exact scheduling.
            std::thread::sleep(Duration::from_millis(30));
            if !disconnect { tx.send(7).unwrap(); }
            drop(tx);
            assert_eq!(completion.recv_timeout(Duration::from_secs(1)).unwrap(), if disconnect { Err(mpsc::RecvTimeoutError::Disconnected) } else { Ok(7) });
            thread.join().unwrap();
        }
      }
    }
    #[test]
    fn forced_fallback_preserves_queue_and_timeout() {
        let (tx, mut rx) = channel();
        rx.initialized = true; rx.disabled = true;
        tx.send(3).unwrap();
        assert_eq!(receive(&mut rx, Duration::from_millis(1)), Ok(3));
        assert_eq!(receive(&mut rx, Duration::from_millis(1)), Err(mpsc::RecvTimeoutError::Timeout));
        drop(tx);
        assert_eq!(receive(&mut rx, Duration::from_secs(1)), Err(mpsc::RecvTimeoutError::Disconnected));
    }
    #[test]
    fn relative_time_rounds_up_without_overflow() {
        assert_eq!(relative_due_time(Duration::ZERO), -1);
        assert_eq!(relative_due_time(Duration::from_nanos(100)), -1);
        assert_eq!(relative_due_time(Duration::from_nanos(101)), -2);
        assert_eq!(relative_due_time(Duration::MAX), -i64::MAX);
        assert_eq!(watchdog_ms(Duration::MAX), u32::MAX - 1);
    }
    #[test]
    fn failed_notification_switches_to_fallback_once() {
        let (_tx, mut rx) = channel::<()>();
        if let Some(notification) = &rx.notification {
            notification.failed.store(true, Ordering::Relaxed);
        }
        let messages = std::cell::RefCell::new(Vec::new());
        for _ in 0..2 {
            assert_eq!(rx.recv_timeout(Duration::from_millis(1), true, &|s| messages.borrow_mut().push(s)), Err(mpsc::RecvTimeoutError::Timeout));
        }
        assert!(rx.disabled);
        assert_eq!(messages.borrow().iter().filter(|s| s.contains("fallback")).count(), 1);
    }
    #[test]
    fn replacement_channel_does_not_share_notification_or_disconnect() {
        let (old, mut old_rx) = channel::<()>();
        let (new, mut new_rx) = channel();
        drop(old);
        assert_eq!(receive(&mut old_rx, Duration::ZERO), Err(mpsc::RecvTimeoutError::Disconnected));
        assert_eq!(receive(&mut new_rx, Duration::ZERO), Err(mpsc::RecvTimeoutError::Timeout));
        new.send(4).unwrap();
        assert_eq!(receive(&mut new_rx, Duration::ZERO), Ok(4));
    }
    #[test]
    #[ignore = "manual timing diagnostic; no VR required"]
    fn measure_wait_intervals() {
        for precise in [false, true] {
          let (_tx, mut rx) = channel::<()>();
          for micros in [16_667, 33_333, 62_500] {
            let mut samples = Vec::new();
            for _ in 0..64 {
                let start = Instant::now();
                assert_eq!(rx.recv_timeout(Duration::from_micros(micros), precise, &|s| println!("{s}")), Err(mpsc::RecvTimeoutError::Timeout));
                samples.push(start.elapsed().as_secs_f64() * 1000.0);
            }
            samples.sort_by(f64::total_cmp);
            println!("precise={precise} target={:.3}ms p50={:.3}ms p95={:.3}ms", micros as f64 / 1000.0, samples[31], samples[60]);
          }
          if precise { assert!(!rx.disabled, "high resolution timer unavailable; measurements are fallback"); }
        }
    }
}
