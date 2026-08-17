use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug)]
pub struct Policy {
    pub policy_version: String,
    pub scanner_db_version: String,
    pub block_severity: String,
    pub trusted_package_sources: Vec<String>,
    pub trusted_registries: Vec<String>,
    pub trusted_dependency_sources: Vec<String>,
    pub require_container_digest: bool,
    pub require_container_signature: bool,
    pub cache_ttl_seconds: u64,
    pub fail_closed: bool,
    pub permit_ttl_seconds: u64,
    pub permit_secret: String,
}

impl Policy {
    pub fn load(path: impl AsRef<Path>) -> Result<Self, String> {
        let text = fs::read_to_string(path.as_ref())
            .map_err(|error| format!("cannot read policy {}: {error}", path.as_ref().display()))?;
        let values = parse_key_values(&text)?;
        Ok(Self {
            policy_version: required(&values, "policy_version")?,
            scanner_db_version: required(&values, "scanner_db_version")?,
            block_severity: required(&values, "block_severity")?.to_ascii_uppercase(),
            trusted_package_sources: list(&values, "trusted_package_sources")?,
            trusted_registries: list(&values, "trusted_registries")?,
            trusted_dependency_sources: list(&values, "trusted_dependency_sources")?,
            require_container_digest: bool_value(&values, "require_container_digest")?,
            require_container_signature: bool_value(&values, "require_container_signature")?,
            cache_ttl_seconds: u64_value(&values, "cache_ttl_seconds")?,
            fail_closed: bool_value(&values, "fail_closed")?,
            permit_ttl_seconds: u64_value(&values, "permit_ttl_seconds")?,
            permit_secret: required(&values, "permit_secret")?,
        })
    }

    pub fn source_is_trusted(&self, kind: &str, source: &str) -> bool {
        let list = match kind {
            "package" => &self.trusted_package_sources,
            "container" => &self.trusted_registries,
            "dependency" => &self.trusted_dependency_sources,
            _ => return false,
        };
        list.iter().any(|candidate| candidate == source)
    }

    pub fn blocks_severity(&self, severity: &str) -> bool {
        severity_rank(severity) >= severity_rank(&self.block_severity)
            && severity_rank(severity) > 0
    }
}

pub fn severity_rank(value: &str) -> u8 {
    match value.trim().to_ascii_uppercase().as_str() {
        "NONE" | "CLEAN" => 0,
        "LOW" => 1,
        "MEDIUM" => 2,
        "HIGH" => 3,
        "CRITICAL" => 4,
        _ => 5,
    }
}

fn parse_key_values(text: &str) -> Result<HashMap<String, String>, String> {
    let mut values = HashMap::new();
    for (line_number, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            return Err(format!("invalid policy line {}: {line}", line_number + 1));
        };
        let key = key.trim();
        if key.is_empty() {
            return Err(format!("empty policy key on line {}", line_number + 1));
        }
        if values.insert(key.to_string(), value.trim().to_string()).is_some() {
            return Err(format!("duplicate policy key {key}"));
        }
    }
    Ok(values)
}

fn required(values: &HashMap<String, String>, key: &str) -> Result<String, String> {
    values
        .get(key)
        .cloned()
        .filter(|value| !value.is_empty())
        .ok_or_else(|| format!("missing policy key {key}"))
}

fn list(values: &HashMap<String, String>, key: &str) -> Result<Vec<String>, String> {
    let raw = required(values, key)?;
    let result: Vec<String> = raw
        .split(',')
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
        .collect();
    if result.is_empty() {
        return Err(format!("policy list {key} must not be empty"));
    }
    Ok(result)
}

fn bool_value(values: &HashMap<String, String>, key: &str) -> Result<bool, String> {
    match required(values, key)?.to_ascii_lowercase().as_str() {
        "true" | "1" | "yes" | "on" => Ok(true),
        "false" | "0" | "no" | "off" => Ok(false),
        other => Err(format!("policy key {key} is not boolean: {other}")),
    }
}

fn u64_value(values: &HashMap<String, String>, key: &str) -> Result<u64, String> {
    required(values, key)?
        .parse::<u64>()
        .map_err(|_| format!("policy key {key} is not an unsigned integer"))
}
