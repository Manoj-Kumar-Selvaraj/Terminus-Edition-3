use crate::model::{Decision, Request};
use crate::policy::Policy;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug)]
pub struct CachedDecision {
    pub allow: bool,
    pub reason: String,
}

fn path(state_dir: impl AsRef<Path>) -> PathBuf {
    state_dir.as_ref().join("cache.tsv")
}

fn cache_key(request: &Request, policy: &Policy) -> String {
    format!(
        "{}|{}|{}|{}|{}|{}|{}",
        request.kind,
        request.name,
        request.version,
        request.source,
        request.digest,
        policy.policy_version,
        policy.scanner_db_version,
    )
}

pub fn lookup(
    state_dir: impl AsRef<Path>,
    request: &Request,
    policy: &Policy,
    now: u64,
) -> Result<Option<CachedDecision>, String> {
    let cache_path = path(state_dir);
    let text = match fs::read_to_string(&cache_path) {
        Ok(value) => value,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(format!("cannot read cache {}: {error}", cache_path.display())),
    };
    let wanted = cache_key(request, policy);
    for raw in text.lines().rev() {
        let fields: Vec<&str> = raw.split('\t').collect();
        if fields.len() != 4 || fields[0] != wanted {
            continue;
        }
        let expires_at = match fields[3].parse::<u64>() {
            Ok(value) => value,
            Err(_) => continue,
        };
        if expires_at < now {
            continue;
        }
        return Ok(Some(CachedDecision {
            allow: fields[1] == "ALLOW",
            reason: fields[2].to_string(),
        }));
    }
    Ok(None)
}

pub fn store(
    state_dir: impl AsRef<Path>,
    request: &Request,
    policy: &Policy,
    decision: &Decision,
    now: u64,
) -> Result<(), String> {
    fs::create_dir_all(state_dir.as_ref())
        .map_err(|error| format!("cannot create state directory: {error}"))?;
    let cache_path = path(state_dir);
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&cache_path)
        .map_err(|error| format!("cannot open cache {}: {error}", cache_path.display()))?;
    let expires_at = now.saturating_add(policy.cache_ttl_seconds);
    writeln!(
        file,
        "{}\t{}\t{}\t{}",
        cache_key(request, policy),
        if decision.allow { "ALLOW" } else { "DENY" },
        decision.reason,
        expires_at
    )
    .map_err(|error| format!("cannot append cache: {error}"))?;
    file.sync_data()
        .map_err(|error| format!("cannot sync cache: {error}"))?;
    Ok(())
}
