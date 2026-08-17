use std::io::{self, BufRead, Write};

pub const MAX_COMMAND_LINE_BYTES: usize = (2 * 1024 * 1024) + (2 * 4096) + 256;

pub struct LineReader<R> {
    inner: R,
    buffer: String,
}

impl<R: BufRead> LineReader<R> {
    pub fn new(inner: R) -> Self {
        Self {
            inner,
            buffer: String::new(),
        }
    }

    pub fn next_command(&mut self) -> io::Result<Option<String>> {
        self.buffer.clear();
        let read = self.inner.read_line(&mut self.buffer)?;
        if read == 0 {
            return Ok(None);
        }
        if self.buffer.len() > MAX_COMMAND_LINE_BYTES {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "command line exceeds protocol limit",
            ));
        }
        trim_line_ending(&mut self.buffer);
        validate_command_bytes(&self.buffer)?;
        Ok(Some(self.buffer.clone()))
    }
}

pub struct LineWriter<W> {
    inner: W,
}

impl<W: Write> LineWriter<W> {
    pub fn new(inner: W) -> Self {
        Self { inner }
    }

    pub fn write_response(&mut self, line: &str) -> io::Result<()> {
        reject_embedded_newline(line)?;
        self.inner.write_all(line.as_bytes())?;
        self.inner.write_all(b"\n")?;
        self.inner.flush()
    }
}

fn trim_line_ending(line: &mut String) {
    if line.ends_with('\n') {
        line.pop();
        if line.ends_with('\r') {
            line.pop();
        }
    }
}

fn reject_embedded_newline(line: &str) -> io::Result<()> {
    if line.contains('\n') || line.contains('\r') {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "response contains an embedded line ending",
        ));
    }
    Ok(())
}

fn validate_command_bytes(line: &str) -> io::Result<()> {
    if line.as_bytes().contains(&0) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "command contains a NUL byte",
        ));
    }
    if !line.is_ascii() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "commands must use ASCII",
        ));
    }
    Ok(())
}
