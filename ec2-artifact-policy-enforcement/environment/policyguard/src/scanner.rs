use std::fs;
use std::path::Path;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ScanResult {
    Observed { max_severity: String },
    Unavailable,
    Unknown,
}

pub fn scan(
    database: impl AsRef<Path>,
    digest: &str,
    requested_status: &str,
) -> Result<ScanResult, String> {
    match requested_status.trim().to_ascii_lowercase().as_str() {
        "unavailable" => return Ok(ScanResult::Unavailable),
        "unknown" => return Ok(ScanResult::Unknown),
        "normal" | "" => {}
        other => return Err(format!("unsupported scanner status {other}")),
    }

    let text = match fs::read_to_string(database.as_ref()) {
        Ok(value) => value,
        Err(_) => return Ok(ScanResult::Unavailable),
    };
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let mut fields = line.split('\t');
        let Some(candidate_digest) = fields.next() else {
            continue;
        };
        let Some(max_severity) = fields.next() else {
            continue;
        };
        if candidate_digest == digest {
            return Ok(ScanResult::Observed {
                max_severity: max_severity.trim().to_ascii_uppercase(),
            });
        }
    }
    Ok(ScanResult::Unknown)
}
