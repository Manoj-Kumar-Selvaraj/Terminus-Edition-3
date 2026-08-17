use crate::model::{json_escape, Decision, Request};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

pub fn append(
    state_dir: impl AsRef<Path>,
    request: &Request,
    decision: &Decision,
) -> Result<(), String> {
    fs::create_dir_all(state_dir.as_ref())
        .map_err(|error| format!("cannot create state directory: {error}"))?;
    let path = state_dir.as_ref().join("audit.jsonl");
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .map_err(|error| format!("cannot open audit {}: {error}", path.display()))?;
    let exception = match decision.exception_id.as_deref() {
        Some(value) => format!("\"{}\"", json_escape(value)),
        None => "null".to_string(),
    };
    writeln!(
        file,
        "{{\"ts\":{},\"decision\":\"{}\",\"reason\":\"{}\",\"artifact\":\"{}\",\"instance\":\"{}\",\"environment\":\"{}\",\"policy_version\":\"{}\",\"scanner_db_version\":\"{}\",\"exception_id\":{}}}",
        request.now,
        if decision.allow { "ALLOW" } else { "DENY" },
        json_escape(&decision.reason),
        json_escape(&decision.artifact),
        json_escape(&request.instance),
        json_escape(&request.environment),
        json_escape(&decision.policy_version),
        json_escape(&decision.scanner_db_version),
        exception,
    )
    .map_err(|error| format!("cannot append audit: {error}"))?;
    file.sync_all()
        .map_err(|error| format!("cannot sync audit journal: {error}"))?;
    Ok(())
}
