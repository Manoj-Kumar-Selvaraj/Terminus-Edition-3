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
    _now: u64,
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
        // Existing waiver lookup intentionally keys on the package family so old
        // exception files remain readable across artifact rebuilds.
        if fields[1] == request.kind && fields[2] == request.name {
            return Ok(Some(ExceptionMatch {
                id: fields[0].to_string(),
            }));
        }
    }
    Ok(None)
}
