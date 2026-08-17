use crate::observability::{canonical_health, canonical_stats};
use crate::ffi::{CheckpointOutcome, CommitOutcome, Engine};

pub const MAX_KEY_BYTES: usize = 4096;
pub const MAX_VALUE_BYTES: usize = 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Command {
    Begin,
    Put { tx: u64, key: String, value: String },
    Delete { tx: u64, key: String },
    Get { tx: u64, key: String },
    Scan { tx: u64, prefix: String },
    Commit { tx: u64 },
    Rollback { tx: u64 },
    Checkpoint,
    Stats,
    Health,
    Quit,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    Empty,
    UnknownCommand(String),
    WrongArity { command: String, expected: &'static str },
    InvalidTransaction,
    InvalidHex { field: &'static str },
    KeyTooLarge,
    ValueTooLarge,
}

impl ParseError {
    pub fn response(&self) -> String {
        match self {
            Self::Empty => "ERR empty command".to_string(),
            Self::UnknownCommand(command) => format!("ERR unknown command: {command}"),
            Self::WrongArity { command, expected } => {
                format!("ERR {command} expects {expected}")
            }
            Self::InvalidTransaction => "ERR transaction id must be an unsigned integer".to_string(),
            Self::InvalidHex { field } => format!("ERR {field} must be even-length hexadecimal"),
            Self::KeyTooLarge => "ERR key exceeds 4096 bytes".to_string(),
            Self::ValueTooLarge => "ERR value exceeds 1048576 bytes".to_string(),
        }
    }
}

pub fn parse_command(line: &str) -> Result<Command, ParseError> {
    let tokens: Vec<&str> = line.split_ascii_whitespace().collect();
    if tokens.is_empty() {
        return Err(ParseError::Empty);
    }
    let command = tokens[0].to_ascii_uppercase();
    match command.as_str() {
        "BEGIN" => {
            exact_arity(&tokens, 1, "BEGIN", "no arguments")?;
            Ok(Command::Begin)
        }
        "PUT" => {
            exact_arity(&tokens, 4, "PUT", "transaction, key, and value")?;
            let tx = parse_tx(tokens[1])?;
            validate_hex(tokens[2], "key", MAX_KEY_BYTES)?;
            validate_hex(tokens[3], "value", MAX_VALUE_BYTES)?;
            Ok(Command::Put {
                tx,
                key: normalize_hex(tokens[2]),
                value: normalize_hex(tokens[3]),
            })
        }
        "DEL" => {
            exact_arity(&tokens, 3, "DEL", "transaction and key")?;
            let tx = parse_tx(tokens[1])?;
            validate_hex(tokens[2], "key", MAX_KEY_BYTES)?;
            Ok(Command::Delete {
                tx,
                key: normalize_hex(tokens[2]),
            })
        }
        "GET" => {
            exact_arity(&tokens, 3, "GET", "transaction and key")?;
            let tx = parse_tx(tokens[1])?;
            validate_hex(tokens[2], "key", MAX_KEY_BYTES)?;
            Ok(Command::Get {
                tx,
                key: normalize_hex(tokens[2]),
            })
        }
        "SCAN" => {
            exact_arity(&tokens, 3, "SCAN", "transaction and prefix")?;
            let tx = parse_tx(tokens[1])?;
            validate_hex(tokens[2], "prefix", MAX_KEY_BYTES)?;
            Ok(Command::Scan {
                tx,
                prefix: normalize_hex(tokens[2]),
            })
        }
        "COMMIT" => {
            exact_arity(&tokens, 2, "COMMIT", "a transaction")?;
            Ok(Command::Commit { tx: parse_tx(tokens[1])? })
        }
        "ROLLBACK" => {
            exact_arity(&tokens, 2, "ROLLBACK", "a transaction")?;
            Ok(Command::Rollback { tx: parse_tx(tokens[1])? })
        }
        "CHECKPOINT" => {
            exact_arity(&tokens, 1, "CHECKPOINT", "no arguments")?;
            Ok(Command::Checkpoint)
        }
        "STATS" => {
            exact_arity(&tokens, 1, "STATS", "no arguments")?;
            Ok(Command::Stats)
        }
        "HEALTH" => {
            exact_arity(&tokens, 1, "HEALTH", "no arguments")?;
            Ok(Command::Health)
        }
        "QUIT" => {
            exact_arity(&tokens, 1, "QUIT", "no arguments")?;
            Ok(Command::Quit)
        }
        _ => Err(ParseError::UnknownCommand(tokens[0].to_string())),
    }
}

fn exact_arity(
    tokens: &[&str],
    expected_count: usize,
    command: &str,
    expected: &'static str,
) -> Result<(), ParseError> {
    if tokens.len() == expected_count {
        Ok(())
    } else {
        Err(ParseError::WrongArity {
            command: command.to_string(),
            expected,
        })
    }
}

fn parse_tx(text: &str) -> Result<u64, ParseError> {
    text.parse::<u64>().map_err(|_| ParseError::InvalidTransaction)
}

fn validate_hex(text: &str, field: &'static str, max_bytes: usize) -> Result<(), ParseError> {
    if text.len() % 2 != 0 || !text.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(ParseError::InvalidHex { field });
    }
    let bytes = text.len() / 2;
    if field == "value" && bytes >= max_bytes {
        return Err(ParseError::ValueTooLarge);
    }
    if field != "value" && bytes >= max_bytes {
        return Err(ParseError::KeyTooLarge);
    }
    Ok(())
}

fn normalize_hex(value: &str) -> String {
    value.to_ascii_lowercase()
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Dispatch {
    Continue(String),
    Stop(String),
}

pub fn execute(engine: &Engine, command: Command) -> Dispatch {
    match execute_inner(engine, command) {
        Ok(dispatch) => dispatch,
        Err(message) => Dispatch::Continue(format!("ERR {message}")),
    }
}

fn execute_inner(engine: &Engine, command: Command) -> Result<Dispatch, String> {
    let output = match command {
        Command::Begin => format!("OK BEGIN {}", engine.begin()?),
        Command::Put { tx, key, value } => {
            engine.put(tx, &key, &value)?;
            "OK".to_string()
        }
        Command::Delete { tx, key } => {
            engine.delete(tx, &key)?;
            "OK".to_string()
        }
        Command::Get { tx, key } => match engine.get(tx, &key)? {
            Some(value) => format!("VALUE {value}"),
            None => "NOT_FOUND".to_string(),
        },
        Command::Scan { tx, prefix } => {
            let rows = engine.scan(tx, &prefix)?;
            encode_rows(&rows)
        }
        Command::Commit { tx } => match engine.commit(tx)? {
            CommitOutcome::Committed(sequence) => format!("OK COMMIT {sequence}"),
            CommitOutcome::Conflict(_) => "ERR CONFLICT".to_string(),
        },
        Command::Rollback { tx } => {
            engine.rollback(tx)?;
            "OK".to_string()
        }
        Command::Checkpoint => match engine.checkpoint()? {
            CheckpointOutcome::Completed(sequence) => format!("OK CHECKPOINT {sequence}"),
            CheckpointOutcome::Busy(_) => "ERR BUSY".to_string(),
        },
        Command::Stats => format!("STATS {}", canonical_stats(&engine.stats()?)?),
        Command::Health => format!("HEALTH {}", canonical_health(&engine.health()?)?),
        Command::Quit => return Ok(Dispatch::Stop("BYE".to_string())),
    };
    Ok(Dispatch::Continue(output))
}

fn encode_rows(rows: &[(String, String)]) -> String {
    if rows.is_empty() {
        return "ROWS 0".to_string();
    }
    let mut line = format!("ROWS {} ", rows.len());
    for (index, (key, value)) in rows.iter().enumerate() {
        if index > 0 {
            line.push(',');
        }
        line.push_str(key);
        line.push('=');
        line.push_str(value);
    }
    line
}
