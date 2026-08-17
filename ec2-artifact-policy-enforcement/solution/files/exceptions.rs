use crate::model::Request;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug)]
pub struct ExceptionMatch {
    pub id: String,
}

pub fn find(
    path: impl AsRef<Path>,
    request: &Request,
    now: u64,
) -> Result<Option<ExceptionMatch>, String> {
    let text = fs::read_to_string(path.as_ref())
        .map_err(|error| format!("cannot read exceptions {}: {error}", path.as_ref().display()))?;
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        if fields.len() != 6 {
            continue;
        }
        let expires_at = match fields[5].parse::<u64>() {
            Ok(value) => value,
            Err(_) => continue,
        };
        if fields[1] == request.kind
            && fields[2] == request.name
            && fields[3] == request.digest
            && fields[4] == request.environment
            && now < expires_at
        {
            return Ok(Some(ExceptionMatch {
                id: fields[0].to_string(),
            }));
        }
    }
    Ok(None)
}
