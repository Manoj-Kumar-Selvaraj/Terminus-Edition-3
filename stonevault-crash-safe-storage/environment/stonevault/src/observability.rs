#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Stats {
    pub commit_seq: u64,
    pub keys: u64,
    pub wal_bytes: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Health {
    pub commit_seq: u64,
    pub keys: u64,
    pub active_tx: u64,
    pub wal_bytes: u64,
    pub snapshot_present: bool,
}

pub fn canonical_stats(raw: &str) -> Result<String, String> {
    let stats = parse_stats(raw)?;
    Ok(format!(
        "commit_seq={} keys={} wal_bytes={}",
        stats.commit_seq, stats.keys, stats.wal_bytes
    ))
}

pub fn canonical_health(raw: &str) -> Result<String, String> {
    let health = parse_health(raw)?;
    Ok(format!(
        "status=ok commit_seq={} keys={} active_tx={} wal_bytes={} snapshot={}",
        health.commit_seq,
        health.keys,
        health.active_tx,
        health.wal_bytes,
        if health.snapshot_present { "present" } else { "absent" }
    ))
}

fn parse_stats(raw: &str) -> Result<Stats, String> {
    let fields = fields(raw)?;
    if fields.len() != 3 {
        return Err("storage returned malformed statistics".to_string());
    }
    Ok(Stats {
        commit_seq: parse_u64(fields[0], "commit_seq")?,
        keys: parse_u64(fields[1], "keys")?,
        wal_bytes: parse_u64(fields[2], "wal_bytes")?,
    })
}

fn parse_health(raw: &str) -> Result<Health, String> {
    let fields = fields(raw)?;
    if fields.len() != 6 || fields[0] != ("status", "ok") {
        return Err("storage returned malformed health status".to_string());
    }
    let snapshot_present = match fields[5] {
        ("snapshot", "present") => true,
        ("snapshot", "absent") => false,
        _ => return Err("storage returned invalid snapshot health state".to_string()),
    };
    Ok(Health {
        commit_seq: parse_u64(fields[1], "commit_seq")?,
        keys: parse_u64(fields[2], "keys")?,
        active_tx: parse_u64(fields[3], "active_tx")?,
        wal_bytes: parse_u64(fields[4], "wal_bytes")?,
        snapshot_present,
    })
}

fn fields(raw: &str) -> Result<Vec<(&str, &str)>, String> {
    let mut output = Vec::new();
    for token in raw.split_ascii_whitespace() {
        let (name, value) = token
            .split_once('=')
            .ok_or_else(|| "storage returned malformed observability field".to_string())?;
        if name.is_empty() || value.is_empty() {
            return Err("storage returned an empty observability field".to_string());
        }
        output.push((name, value));
    }
    Ok(output)
}

fn parse_u64(field: (&str, &str), expected_name: &str) -> Result<u64, String> {
    if field.0 != expected_name {
        return Err(format!("storage returned unexpected field: {}", field.0));
    }
    field
        .1
        .parse::<u64>()
        .map_err(|_| format!("storage returned invalid {expected_name}"))
}
