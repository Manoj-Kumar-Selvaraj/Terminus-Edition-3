use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::ptr::NonNull;

const ERR_CAPACITY: usize = 1024;

unsafe extern "C" {
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
    ) -> c_int;
    fn sv_del(
        handle: *mut c_void,
        tx_id: u64,
        key_hex: *const c_char,
        err: *mut c_char,
        err_len: usize,
    ) -> c_int;
    fn sv_get(
        handle: *mut c_void,
        tx_id: u64,
        key_hex: *const c_char,
        status: *mut c_int,
        err: *mut c_char,
        err_len: usize,
    ) -> *mut c_char;
    fn sv_scan(
        handle: *mut c_void,
        tx_id: u64,
        prefix_hex: *const c_char,
        status: *mut c_int,
        err: *mut c_char,
        err_len: usize,
    ) -> *mut c_char;
    fn sv_commit(
        handle: *mut c_void,
        tx_id: u64,
        commit_seq: *mut u64,
        err: *mut c_char,
        err_len: usize,
    ) -> c_int;
    fn sv_rollback(handle: *mut c_void, tx_id: u64, err: *mut c_char, err_len: usize) -> c_int;
    fn sv_checkpoint(
        handle: *mut c_void,
        checkpoint_seq: *mut u64,
        err: *mut c_char,
        err_len: usize,
    ) -> c_int;
    fn sv_stats(handle: *mut c_void, err: *mut c_char, err_len: usize) -> *mut c_char;
    fn sv_health(handle: *mut c_void, err: *mut c_char, err_len: usize) -> *mut c_char;
    fn sv_free_string(value: *mut c_char);
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommitOutcome {
    Committed(u64),
    Conflict(u64),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckpointOutcome {
    Completed(u64),
    Busy(u64),
}

pub struct Engine {
    handle: NonNull<c_void>,
}

impl Engine {
    pub fn open(data_dir: &str) -> Result<Self, String> {
        let path = CString::new(data_dir)
            .map_err(|_| "data directory contains an invalid byte".to_string())?;
        let mut err = ErrorBuffer::new();
        let raw = unsafe { sv_open(path.as_ptr(), err.as_mut_ptr(), err.capacity()) };
        let handle = NonNull::new(raw).ok_or_else(|| err.message_or("cannot open database"))?;
        Ok(Self { handle })
    }

    pub fn current_sequence(&self) -> u64 {
        unsafe { sv_current_sequence(self.handle.as_ptr()) }
    }

    pub fn begin(&self) -> Result<u64, String> {
        let mut err = ErrorBuffer::new();
        let tx = unsafe { sv_begin(self.handle.as_ptr(), err.as_mut_ptr(), err.capacity()) };
        if tx == 0 {
            Err(err.message_or("cannot begin transaction"))
        } else {
            Ok(tx)
        }
    }

    pub fn put(&self, tx: u64, key: &str, value: &str) -> Result<(), String> {
        let key = c_text(key, "key")?;
        let value = c_text(value, "value")?;
        let mut err = ErrorBuffer::new();
        let rc = unsafe {
            sv_put(
                self.handle.as_ptr(),
                tx,
                key.as_ptr(),
                value.as_ptr(),
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        status_zero(rc, err, "put failed")
    }

    pub fn delete(&self, tx: u64, key: &str) -> Result<(), String> {
        let key = c_text(key, "key")?;
        let mut err = ErrorBuffer::new();
        let rc = unsafe {
            sv_del(
                self.handle.as_ptr(),
                tx,
                key.as_ptr(),
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        status_zero(rc, err, "delete failed")
    }

    pub fn get(&self, tx: u64, key: &str) -> Result<Option<String>, String> {
        let key = c_text(key, "key")?;
        let mut err = ErrorBuffer::new();
        let mut status: c_int = -1;
        let raw = unsafe {
            sv_get(
                self.handle.as_ptr(),
                tx,
                key.as_ptr(),
                &mut status,
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        match status {
            0 => {
                if !raw.is_null() {
                    unsafe { sv_free_string(raw) };
                    return Err("storage returned unexpected value for missing key".to_string());
                }
                Ok(None)
            }
            1 => Ok(Some(take_owned_string(raw)?)),
            _ => {
                if !raw.is_null() {
                    unsafe { sv_free_string(raw) };
                }
                Err(err.message_or("get failed"))
            }
        }
    }

    pub fn scan(&self, tx: u64, prefix: &str) -> Result<Vec<(String, String)>, String> {
        let prefix = c_text(prefix, "prefix")?;
        let mut err = ErrorBuffer::new();
        let mut status: c_int = -1;
        let raw = unsafe {
            sv_scan(
                self.handle.as_ptr(),
                tx,
                prefix.as_ptr(),
                &mut status,
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        if status != 0 {
            if !raw.is_null() {
                unsafe { sv_free_string(raw) };
            }
            return Err(err.message_or("scan failed"));
        }
        let encoded = take_owned_string(raw)?;
        parse_rows(&encoded)
    }

    pub fn commit(&self, tx: u64) -> Result<CommitOutcome, String> {
        let mut err = ErrorBuffer::new();
        let mut sequence = 0_u64;
        let rc = unsafe {
            sv_commit(
                self.handle.as_ptr(),
                tx,
                &mut sequence,
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        match rc {
            0 => Ok(CommitOutcome::Committed(sequence)),
            1 => Ok(CommitOutcome::Conflict(sequence)),
            _ => Err(err.message_or("commit failed")),
        }
    }

    pub fn rollback(&self, tx: u64) -> Result<(), String> {
        let mut err = ErrorBuffer::new();
        let rc = unsafe {
            sv_rollback(
                self.handle.as_ptr(),
                tx,
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        status_zero(rc, err, "rollback failed")
    }

    pub fn checkpoint(&self) -> Result<CheckpointOutcome, String> {
        let mut err = ErrorBuffer::new();
        let mut sequence = 0_u64;
        let rc = unsafe {
            sv_checkpoint(
                self.handle.as_ptr(),
                &mut sequence,
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        match rc {
            0 => Ok(CheckpointOutcome::Completed(sequence)),
            1 => Ok(CheckpointOutcome::Busy(sequence)),
            _ => Err(err.message_or("checkpoint failed")),
        }
    }

    pub fn stats(&self) -> Result<String, String> {
        let mut err = ErrorBuffer::new();
        let raw = unsafe {
            sv_stats(
                self.handle.as_ptr(),
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        if raw.is_null() {
            return Err(err.message_or("stats failed"));
        }
        take_owned_string(raw)
    }

    pub fn health(&self) -> Result<String, String> {
        let mut err = ErrorBuffer::new();
        let raw = unsafe {
            sv_health(
                self.handle.as_ptr(),
                err.as_mut_ptr(),
                err.capacity(),
            )
        };
        if raw.is_null() {
            return Err(err.message_or("health failed"));
        }
        take_owned_string(raw)
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        unsafe { sv_close(self.handle.as_ptr()) };
    }
}

struct ErrorBuffer {
    bytes: Vec<c_char>,
}

impl ErrorBuffer {
    fn new() -> Self {
        Self {
            bytes: vec![0; ERR_CAPACITY],
        }
    }

    fn as_mut_ptr(&mut self) -> *mut c_char {
        self.bytes.as_mut_ptr()
    }

    fn capacity(&self) -> usize {
        self.bytes.len()
    }

    fn message_or(&self, fallback: &str) -> String {
        let text = unsafe { CStr::from_ptr(self.bytes.as_ptr()) }
            .to_string_lossy()
            .trim()
            .to_string();
        if text.is_empty() {
            fallback.to_string()
        } else {
            text
        }
    }
}

fn status_zero(rc: c_int, err: ErrorBuffer, fallback: &str) -> Result<(), String> {
    if rc == 0 {
        Ok(())
    } else {
        Err(err.message_or(fallback))
    }
}

fn c_text(value: &str, field: &str) -> Result<CString, String> {
    CString::new(value).map_err(|_| format!("{field} contains an invalid byte"))
}

fn take_owned_string(raw: *mut c_char) -> Result<String, String> {
    if raw.is_null() {
        return Err("storage returned a null string".to_string());
    }
    let text = unsafe { CStr::from_ptr(raw) }
        .to_string_lossy()
        .into_owned();
    unsafe { sv_free_string(raw) };
    Ok(text)
}

fn parse_rows(encoded: &str) -> Result<Vec<(String, String)>, String> {
    if encoded.is_empty() {
        return Ok(Vec::new());
    }
    let mut rows = Vec::new();
    for row in encoded.split(',') {
        let (key, value) = row
            .split_once('=')
            .ok_or_else(|| "storage returned malformed scan row".to_string())?;
        if key.is_empty() {
            return Err("storage returned an empty scan key".to_string());
        }
        rows.push((key.to_string(), value.to_string()));
    }
    Ok(rows)
}
