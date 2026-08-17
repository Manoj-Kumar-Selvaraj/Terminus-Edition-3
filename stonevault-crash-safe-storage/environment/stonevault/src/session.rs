use std::collections::BTreeSet;

use crate::protocol::Command;

#[derive(Debug, Default)]
pub struct SessionState {
    active_transactions: BTreeSet<u64>,
    commands_seen: u64,
    errors_seen: u64,
}

impl SessionState {
    pub fn before_dispatch(&mut self, command: &Command) -> Result<(), String> {
        self.commands_seen = self.commands_seen.saturating_add(1);
        match command {
            Command::Put { tx, .. }
            | Command::Delete { tx, .. }
            | Command::Get { tx, .. }
            | Command::Scan { tx, .. }
            | Command::Commit { tx }
            | Command::Rollback { tx } => {
                if !self.active_transactions.contains(tx) {
                    return Err("unknown transaction".to_string());
                }
            }
            Command::Begin | Command::Checkpoint | Command::Stats | Command::Health | Command::Quit => {}
        }
        Ok(())
    }

    pub fn record_begin(&mut self, response: &str) {
        if let Some(id) = response.strip_prefix("OK BEGIN ") {
            if let Ok(id) = id.parse::<u64>() {
                self.active_transactions.insert(id);
            }
        }
    }

    pub fn after_dispatch(&mut self, command: &Command, response: &str) {
        match command {
            Command::Commit { tx } => {
                if response.starts_with("OK COMMIT ") || response == "ERR CONFLICT" {
                    self.active_transactions.remove(tx);
                }
            }
            Command::Rollback { tx } => {
                if response == "OK" {
                    self.active_transactions.remove(tx);
                }
            }
            _ => {}
        }
        if response.starts_with("ERR ") {
            self.errors_seen = self.errors_seen.saturating_add(1);
        }
    }

    pub fn register_parse_error(&mut self) {
        self.commands_seen = self.commands_seen.saturating_add(1);
        self.errors_seen = self.errors_seen.saturating_add(1);
    }

    pub fn active_count(&self) -> usize {
        self.active_transactions.len()
    }

    pub fn commands_seen(&self) -> u64 {
        self.commands_seen
    }

    pub fn errors_seen(&self) -> u64 {
        self.errors_seen
    }
}
