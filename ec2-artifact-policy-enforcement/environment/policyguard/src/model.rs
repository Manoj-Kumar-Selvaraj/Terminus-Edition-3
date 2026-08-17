use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct Request {
    pub kind: String,
    pub name: String,
    pub version: String,
    pub source: String,
    pub digest: String,
    pub instance: String,
    pub environment: String,
    pub now: u64,
    pub signed: bool,
    pub scanner_status: String,
}

impl Request {
    pub fn from_args(args: &[String]) -> Result<Self, String> {
        let flags = parse_flags(args);
        let required = |key: &str| -> Result<String, String> {
            flags
                .get(key)
                .cloned()
                .ok_or_else(|| format!("missing required flag --{key}"))
        };
        let now = required("now")?
            .parse::<u64>()
            .map_err(|_| "--now must be an unsigned epoch value".to_string())?;
        let signed = flags
            .get("signed")
            .map(|value| parse_bool(value))
            .transpose()?
            .unwrap_or(true);
        Ok(Self {
            kind: required("kind")?,
            name: required("name")?,
            version: required("version")?,
            source: required("source")?,
            digest: required("digest")?,
            instance: required("instance")?,
            environment: required("environment")?,
            now,
            signed,
            scanner_status: flags
                .get("scanner-status")
                .cloned()
                .unwrap_or_else(|| "normal".to_string()),
        })
    }

    pub fn artifact(&self) -> String {
        format!("{}:{}@{}#{}", self.kind, self.name, self.version, self.digest)
    }
}

#[derive(Clone, Debug)]
pub struct Decision {
    pub allow: bool,
    pub reason: String,
    pub artifact: String,
    pub cache_hit: bool,
    pub policy_version: String,
    pub scanner_db_version: String,
    pub exception_id: Option<String>,
    pub permit: Option<String>,
}

impl Decision {
    pub fn new(
        allow: bool,
        reason: impl Into<String>,
        request: &Request,
        policy_version: impl Into<String>,
        scanner_db_version: impl Into<String>,
    ) -> Self {
        Self {
            allow,
            reason: reason.into(),
            artifact: request.artifact(),
            cache_hit: false,
            policy_version: policy_version.into(),
            scanner_db_version: scanner_db_version.into(),
            exception_id: None,
            permit: None,
        }
    }

    pub fn to_json(&self) -> String {
        let exception_id = optional_json_string(self.exception_id.as_deref());
        let permit = optional_json_string(self.permit.as_deref());
        format!(
            "{{\"decision\":\"{}\",\"reason\":\"{}\",\"artifact\":\"{}\",\"cache_hit\":{},\"policy_version\":\"{}\",\"scanner_db_version\":\"{}\",\"exception_id\":{},\"permit\":{}}}",
            if self.allow { "ALLOW" } else { "DENY" },
            json_escape(&self.reason),
            json_escape(&self.artifact),
            if self.cache_hit { "true" } else { "false" },
            json_escape(&self.policy_version),
            json_escape(&self.scanner_db_version),
            exception_id,
            permit,
        )
    }
}

pub fn parse_flags(args: &[String]) -> HashMap<String, String> {
    let mut flags = HashMap::new();
    let mut index = 0;
    while index < args.len() {
        let token = &args[index];
        if !token.starts_with("--") {
            index += 1;
            continue;
        }
        let key = token.trim_start_matches("--").to_string();
        if index + 1 < args.len() && !args[index + 1].starts_with("--") {
            flags.insert(key, args[index + 1].clone());
            index += 2;
        } else {
            flags.insert(key, "true".to_string());
            index += 1;
        }
    }
    flags
}

pub fn parse_bool(value: &str) -> Result<bool, String> {
    match value.trim().to_ascii_lowercase().as_str() {
        "1" | "true" | "yes" | "on" => Ok(true),
        "0" | "false" | "no" | "off" => Ok(false),
        _ => Err(format!("invalid boolean value {value:?}")),
    }
}

pub fn json_escape(value: &str) -> String {
    let mut out = String::with_capacity(value.len());
    for ch in value.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            other => out.push(other),
        }
    }
    out
}

fn optional_json_string(value: Option<&str>) -> String {
    match value {
        Some(text) => format!("\"{}\"", json_escape(text)),
        None => "null".to_string(),
    }
}
