use std::env;
use std::ffi::{c_char, c_void, CStr, CString};
use std::io::{self, BufRead, Write};

const ERR_CAP: usize = 512;

extern "C" {
    fn sv_open(data_dir: *const c_char, err: *mut c_char, err_len: usize) -> *mut c_void;
    fn sv_close(handle: *mut c_void);
    fn sv_current_sequence(handle: *mut c_void) -> u64;
    fn sv_begin(handle: *mut c_void, err: *mut c_char, err_len: usize) -> u64;
    fn sv_put(
        handle: *mut c_void,
        tx_id: u64,
        key_hex: *const c_char,
        value_hex: *const c_char,
        err: *mut c_char,
        err_len: usize,
    ) -> i32;
    fn sv_del(
        handle: *mut c_void,
        tx_id: u64,
        key_hex: *const c_char,
        err: *mut c_char,
        err_len: usize,
    ) -> i32;
    fn sv_get(
        handle: *mut c_void,
        tx_id: u64,
        key_hex: *const c_char,
        status: *mut i32,
        err: *mut c_char,
        err_len: usize,
    ) -> *mut c_char;
    fn sv_scan(
        handle: *mut c_void,
        tx_id: u64,
        prefix_hex: *const c_char,
        status: *mut i32,
        err: *mut c_char,
        err_len: usize,
    ) -> *mut c_char;
    fn sv_commit(
        handle: *mut c_void,
        tx_id: u64,
        commit_seq: *mut u64,
        err: *mut c_char,
        err_len: usize,
    ) -> i32;
    fn sv_rollback(handle: *mut c_void, tx_id: u64, err: *mut c_char, err_len: usize) -> i32;
    fn sv_checkpoint(
        handle: *mut c_void,
        checkpoint_seq: *mut u64,
        err: *mut c_char,
        err_len: usize,
    ) -> i32;
    fn sv_stats(handle: *mut c_void, err: *mut c_char, err_len: usize) -> *mut c_char;
    fn sv_free_string(value: *mut c_char);
}

struct Engine {
    handle: *mut c_void,
}

impl Drop for Engine {
    fn drop(&mut self) {
        unsafe { sv_close(self.handle) };
    }
}

fn error_buffer() -> Vec<c_char> {
    vec![0; ERR_CAP]
}

fn error_text(buffer: &[c_char]) -> String {
    unsafe { CStr::from_ptr(buffer.as_ptr()) }
        .to_string_lossy()
        .into_owned()
}

fn validate_hex(value: &str, field: &str) -> Result<(), String> {
    if value.len() % 2 != 0 || !value.bytes().all(|c| c.is_ascii_hexdigit()) {
        return Err(format!("{field} must be even-length hexadecimal"));
    }
    Ok(())
}

fn c_hex(value: &str, field: &str) -> Result<CString, String> {
    validate_hex(value, field)?;
    CString::new(value).map_err(|_| format!("{field} contains an invalid byte"))
}

fn parse_tx(value: Option<&&str>) -> Result<u64, String> {
    value
        .ok_or_else(|| "transaction id is required".to_string())?
        .parse::<u64>()
        .map_err(|_| "transaction id must be an unsigned integer".to_string())
}

unsafe fn take_string(ptr: *mut c_char) -> String {
    if ptr.is_null() {
        return String::new();
    }
    let value = CStr::from_ptr(ptr).to_string_lossy().into_owned();
    sv_free_string(ptr);
    value
}

fn open_engine(data_dir: &str) -> Result<Engine, String> {
    let data_dir = CString::new(data_dir).map_err(|_| "data directory contains an invalid byte".to_string())?;
    let mut err = error_buffer();
    let handle = unsafe { sv_open(data_dir.as_ptr(), err.as_mut_ptr(), err.len()) };
    if handle.is_null() {
        return Err(error_text(&err));
    }
    Ok(Engine { handle })
}

fn respond(line: &str) {
    println!("{line}");
    let _ = io::stdout().flush();
}

fn execute(engine: &Engine, parts: &[&str]) -> bool {
    if parts.is_empty() {
        respond("ERR empty command");
        return true;
    }
    match parts[0] {
        "BEGIN" if parts.len() == 1 => {
            let mut err = error_buffer();
            let tx = unsafe { sv_begin(engine.handle, err.as_mut_ptr(), err.len()) };
            if tx == 0 {
                respond(&format!("ERR {}", error_text(&err)));
            } else {
                respond(&format!("OK BEGIN {tx}"));
            }
        }
        "PUT" if parts.len() == 4 => {
            let result = (|| {
                let tx = parse_tx(parts.get(1))?;
                let key = c_hex(parts[2], "key")?;
                let value = c_hex(parts[3], "value")?;
                let mut err = error_buffer();
                let rc = unsafe {
                    sv_put(engine.handle, tx, key.as_ptr(), value.as_ptr(), err.as_mut_ptr(), err.len())
                };
                if rc == 0 { Ok(()) } else { Err(error_text(&err)) }
            })();
            match result {
                Ok(()) => respond("OK"),
                Err(message) => respond(&format!("ERR {message}")),
            }
        }
        "DEL" if parts.len() == 3 => {
            let result = (|| {
                let tx = parse_tx(parts.get(1))?;
                let key = c_hex(parts[2], "key")?;
                let mut err = error_buffer();
                let rc = unsafe { sv_del(engine.handle, tx, key.as_ptr(), err.as_mut_ptr(), err.len()) };
                if rc == 0 { Ok(()) } else { Err(error_text(&err)) }
            })();
            match result {
                Ok(()) => respond("OK"),
                Err(message) => respond(&format!("ERR {message}")),
            }
        }
        "GET" if parts.len() == 3 => {
            let result = (|| {
                let tx = parse_tx(parts.get(1))?;
                let key = c_hex(parts[2], "key")?;
                let mut status = -1;
                let mut err = error_buffer();
                let ptr = unsafe {
                    sv_get(
                        engine.handle,
                        tx,
                        key.as_ptr(),
                        &mut status,
                        err.as_mut_ptr(),
                        err.len(),
                    )
                };
                match status {
                    1 => Ok(Some(unsafe { take_string(ptr) })),
                    0 => Ok(None),
                    _ => Err(error_text(&err)),
                }
            })();
            match result {
                Ok(Some(value)) => respond(&format!("VALUE {value}")),
                Ok(None) => respond("NOT_FOUND"),
                Err(message) => respond(&format!("ERR {message}")),
            }
        }
        "SCAN" if parts.len() == 3 => {
            let result = (|| {
                let tx = parse_tx(parts.get(1))?;
                let prefix = c_hex(parts[2], "prefix")?;
                let mut status = -1;
                let mut err = error_buffer();
                let ptr = unsafe {
                    sv_scan(
                        engine.handle,
                        tx,
                        prefix.as_ptr(),
                        &mut status,
                        err.as_mut_ptr(),
                        err.len(),
                    )
                };
                if status != 0 {
                    return Err(error_text(&err));
                }
                Ok(unsafe { take_string(ptr) })
            })();
            match result {
                Ok(rows) => {
                    let count = if rows.is_empty() { 0 } else { rows.split(',').count() };
                    if rows.is_empty() {
                        respond("ROWS 0");
                    } else {
                        respond(&format!("ROWS {count} {rows}"));
                    }
                }
                Err(message) => respond(&format!("ERR {message}")),
            }
        }
        "COMMIT" if parts.len() == 2 => {
            let result = (|| {
                let tx = parse_tx(parts.get(1))?;
                let mut seq = 0;
                let mut err = error_buffer();
                let rc = unsafe {
                    sv_commit(engine.handle, tx, &mut seq, err.as_mut_ptr(), err.len())
                };
                match rc {
                    0 => Ok(Some(seq)),
                    1 => Ok(None),
                    _ => Err(error_text(&err)),
                }
            })();
            match result {
                Ok(Some(seq)) => respond(&format!("OK COMMIT {seq}")),
                Ok(None) => respond("ERR CONFLICT"),
                Err(message) => respond(&format!("ERR {message}")),
            }
        }
        "ROLLBACK" if parts.len() == 2 => {
            let result = (|| {
                let tx = parse_tx(parts.get(1))?;
                let mut err = error_buffer();
                let rc = unsafe { sv_rollback(engine.handle, tx, err.as_mut_ptr(), err.len()) };
                if rc == 0 { Ok(()) } else { Err(error_text(&err)) }
            })();
            match result {
                Ok(()) => respond("OK"),
                Err(message) => respond(&format!("ERR {message}")),
            }
        }
        "CHECKPOINT" if parts.len() == 1 => {
            let mut seq = 0;
            let mut err = error_buffer();
            let rc = unsafe { sv_checkpoint(engine.handle, &mut seq, err.as_mut_ptr(), err.len()) };
            match rc {
                0 => respond(&format!("OK CHECKPOINT {seq}")),
                1 => respond("ERR BUSY"),
                _ => respond(&format!("ERR {}", error_text(&err))),
            }
        }
        "STATS" if parts.len() == 1 => {
            let mut err = error_buffer();
            let ptr = unsafe { sv_stats(engine.handle, err.as_mut_ptr(), err.len()) };
            if ptr.is_null() {
                respond(&format!("ERR {}", error_text(&err)));
            } else {
                let value = unsafe { take_string(ptr) };
                respond(&format!("STATS {value}"));
            }
        }
        "QUIT" if parts.len() == 1 => {
            respond("BYE");
            return false;
        }
        _ => respond("ERR invalid command"),
    }
    true
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut data_dir = env::var("STONEVAULT_DATA").unwrap_or_else(|_| "/app/stonevault/data".to_string());
    let mut i = 1;
    while i < args.len() {
        if args[i] == "--data-dir" && i + 1 < args.len() {
            data_dir = args[i + 1].clone();
            i += 2;
        } else {
            eprintln!("usage: stonevault [--data-dir PATH]");
            std::process::exit(2);
        }
    }

    let engine = match open_engine(&data_dir) {
        Ok(engine) => engine,
        Err(message) => {
            eprintln!("open failed: {message}");
            std::process::exit(1);
        }
    };

    let sequence = unsafe { sv_current_sequence(engine.handle) };
    respond(&format!("READY {sequence}"));

    let stdin = io::stdin();
    for line in stdin.lock().lines() {
        match line {
            Ok(line) => {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if !execute(&engine, &parts) {
                    break;
                }
            }
            Err(error) => {
                eprintln!("stdin error: {error}");
                std::process::exit(1);
            }
        }
    }
}
