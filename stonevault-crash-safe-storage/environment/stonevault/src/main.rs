mod config;
mod ffi;
mod line_io;
mod observability;
mod protocol;
mod session;

use std::io;

use config::RuntimeConfig;
use ffi::Engine;
use line_io::{LineReader, LineWriter};
use protocol::{execute, parse_command, Command, Dispatch};
use session::SessionState;

fn run() -> Result<(), String> {
    let config = RuntimeConfig::from_process()?;
    let data_dir = config.data_dir.to_string_lossy().into_owned();
    let engine = Engine::open(&data_dir)?;
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut reader = LineReader::new(stdin.lock());
    let mut writer = LineWriter::new(stdout.lock());
    writer
        .write_response(&format!("READY {}", engine.current_sequence()))
        .map_err(|error| format!("cannot write READY response: {error}"))?;

    let mut session = SessionState::default();
    while let Some(line) = reader
        .next_command()
        .map_err(|error| format!("cannot read command: {error}"))?
    {
        let command = match parse_command(&line) {
            Ok(command) => command,
            Err(error) => {
                session.register_parse_error();
                writer.write_response(&error.response())
                    .map_err(|io_error| format!("cannot write response: {io_error}"))?;
                continue;
            }
        };

        if let Err(message) = session.before_dispatch(&command) {
            writer.write_response(&format!("ERR {message}"))
                .map_err(|error| format!("cannot write response: {error}"))?;
            continue;
        }

        let command_copy = command.clone();
        let dispatch = execute(&engine, command);
        match dispatch {
            Dispatch::Continue(response) => {
                if matches!(command_copy, Command::Begin) {
                    session.record_begin(&response);
                }
                session.after_dispatch(&command_copy, &response);
                writer.write_response(&response)
                    .map_err(|error| format!("cannot write response: {error}"))?;
            }
            Dispatch::Stop(response) => {
                writer.write_response(&response)
                    .map_err(|error| format!("cannot write response: {error}"))?;
                return Ok(());
            }
        }
    }
    Ok(())
}

fn main() {
    if let Err(message) = run() {
        eprintln!("{message}");
        std::process::exit(1);
    }
}
