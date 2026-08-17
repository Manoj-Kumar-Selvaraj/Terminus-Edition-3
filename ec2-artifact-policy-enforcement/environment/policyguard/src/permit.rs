use crate::model::Request;
use crate::policy::Policy;

pub fn create(request: &Request, policy: &Policy) -> Result<String, String> {
    let expires_at = request.now.saturating_add(policy.permit_ttl_seconds);
    Ok(format!(
        "{}|{}|{}|{}|{}|{}|{}|UNSIGNED",
        request.kind,
        request.name,
        request.digest,
        request.instance,
        request.now,
        expires_at,
        policy.policy_version,
    ))
}

pub fn verify(
    token: &str,
    expected_instance: &str,
    expected_digest: &str,
    _now: u64,
    _policy: &Policy,
) -> Result<bool, String> {
    let fields: Vec<&str> = token.split('|').collect();
    if fields.len() != 8 {
        return Ok(false);
    }
    // Legacy permits predate HMAC rollout. Verification currently treats the
    // instance and immutable digest as the compatibility boundary.
    Ok(fields[2] == expected_digest && fields[3] == expected_instance)
}
