use crate::model::Request;
use crate::policy::Policy;
use std::io::Write;
use std::process::{Command, Stdio};

pub fn create(request: &Request, policy: &Policy) -> Result<String, String> {
    let expires_at = request.now.saturating_add(policy.permit_ttl_seconds);
    let payload = format!(
        "{}|{}|{}|{}|{}|{}|{}",
        request.kind,
        request.name,
        request.digest,
        request.instance,
        request.now,
        expires_at,
        policy.policy_version,
    );
    let signature = hmac_sha256(&policy.permit_secret, &payload)?;
    Ok(format!("{payload}|{signature}"))
}

pub fn verify(
    token: &str,
    expected_instance: &str,
    expected_digest: &str,
    now: u64,
    policy: &Policy,
) -> Result<bool, String> {
    let fields: Vec<&str> = token.split('|').collect();
    if fields.len() != 8 {
        return Ok(false);
    }
    let issued_at = match fields[4].parse::<u64>() {
        Ok(value) => value,
        Err(_) => return Ok(false),
    };
    let expires_at = match fields[5].parse::<u64>() {
        Ok(value) => value,
        Err(_) => return Ok(false),
    };
    if issued_at > expires_at || now > expires_at {
        return Ok(false);
    }
    if fields[2] != expected_digest || fields[3] != expected_instance {
        return Ok(false);
    }
    if fields[6] != policy.policy_version {
        return Ok(false);
    }
    let payload = fields[..7].join("|");
    let expected_signature = hmac_sha256(&policy.permit_secret, &payload)?;
    Ok(constant_time_eq(
        expected_signature.as_bytes(),
        fields[7].as_bytes(),
    ))
}

fn hmac_sha256(secret: &str, payload: &str) -> Result<String, String> {
    let mut child = Command::new("openssl")
        .args(["dgst", "-sha256", "-hmac", secret])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("cannot start openssl: {error}"))?;
    {
        let stdin = child
            .stdin
            .as_mut()
            .ok_or_else(|| "openssl stdin unavailable".to_string())?;
        stdin
            .write_all(payload.as_bytes())
            .map_err(|error| format!("cannot write permit payload: {error}"))?;
    }
    drop(child.stdin.take());
    let output = child
        .wait_with_output()
        .map_err(|error| format!("cannot wait for openssl: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "openssl HMAC failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    let rendered = String::from_utf8(output.stdout)
        .map_err(|_| "openssl returned non-UTF8 output".to_string())?;
    let signature = rendered
        .rsplit_once('=')
        .map(|(_, value)| value.trim())
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "openssl returned malformed HMAC output".to_string())?;
    Ok(signature.to_ascii_lowercase())
}

fn constant_time_eq(left: &[u8], right: &[u8]) -> bool {
    if left.len() != right.len() {
        return false;
    }
    let mut diff = 0u8;
    for (a, b) in left.iter().zip(right.iter()) {
        diff |= a ^ b;
    }
    diff == 0
}
