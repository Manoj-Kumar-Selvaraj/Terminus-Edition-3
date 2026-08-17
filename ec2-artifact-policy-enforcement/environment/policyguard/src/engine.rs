use crate::adapters;
use crate::audit;
use crate::cache;
use crate::exceptions;
use crate::model::{Decision, Request};
use crate::permit;
use crate::policy::Policy;
use crate::scanner::{self, ScanResult};
use std::path::Path;

pub struct EnginePaths<'a> {
    pub policy: &'a Path,
    pub scanner_db: &'a Path,
    pub exceptions: &'a Path,
    pub state_dir: &'a Path,
}

pub fn evaluate(paths: &EnginePaths<'_>, request: &Request) -> Result<Decision, String> {
    let policy = Policy::load(paths.policy)?;

    if request.digest.trim().is_empty() {
        return finalize(
            paths,
            request,
            &policy,
            Decision::new(
                false,
                "IMMUTABLE_ID_REQUIRED",
                request,
                &policy.policy_version,
                &policy.scanner_db_version,
            ),
            false,
        );
    }

    if request.kind == "container" && policy.require_container_digest && request.digest.is_empty() {
        return finalize(
            paths,
            request,
            &policy,
            Decision::new(
                false,
                "IMMUTABLE_ID_REQUIRED",
                request,
                &policy.policy_version,
                &policy.scanner_db_version,
            ),
            false,
        );
    }

    if let Err(reason) = adapters::validate(&policy, request) {
        return finalize(
            paths,
            request,
            &policy,
            Decision::new(
                false,
                reason,
                request,
                &policy.policy_version,
                &policy.scanner_db_version,
            ),
            false,
        );
    }

    if let Some(cached) = cache::lookup(paths.state_dir, request, &policy, request.now)? {
        let mut decision = Decision::new(
            cached.allow,
            cached.reason,
            request,
            &policy.policy_version,
            &policy.scanner_db_version,
        );
        decision.cache_hit = true;
        if decision.allow {
            decision.permit = Some(permit::create(request, &policy)?);
        }
        audit::append(paths.state_dir, request, &decision)?;
        return Ok(decision);
    }

    let mut decision = match scanner::scan(paths.scanner_db, &request.digest, &request.scanner_status)? {
        ScanResult::Unavailable => Decision::new(
            true,
            "SCANNER_UNAVAILABLE_FAIL_OPEN",
            request,
            &policy.policy_version,
            &policy.scanner_db_version,
        ),
        ScanResult::Unknown => Decision::new(
            true,
            "SCANNER_UNKNOWN_FAIL_OPEN",
            request,
            &policy.policy_version,
            &policy.scanner_db_version,
        ),
        ScanResult::Observed { max_severity } => {
            if policy.blocks_severity(&max_severity) {
                if let Some(exception) = exceptions::find(paths.exceptions, request, request.now)? {
                    let mut allowed = Decision::new(
                        true,
                        "EXCEPTION_ALLOW",
                        request,
                        &policy.policy_version,
                        &policy.scanner_db_version,
                    );
                    allowed.exception_id = Some(exception.id);
                    allowed
                } else {
                    Decision::new(
                        false,
                        "VULNERABILITY_THRESHOLD_EXCEEDED",
                        request,
                        &policy.policy_version,
                        &policy.scanner_db_version,
                    )
                }
            } else {
                Decision::new(
                    true,
                    "POLICY_ALLOW",
                    request,
                    &policy.policy_version,
                    &policy.scanner_db_version,
                )
            }
        }
    };

    if decision.allow {
        decision.permit = Some(permit::create(request, &policy)?);
    }
    let cacheable = decision.exception_id.is_none();
    if cacheable {
        cache::store(paths.state_dir, request, &policy, &decision, request.now)?;
    }
    audit::append(paths.state_dir, request, &decision)?;
    Ok(decision)
}

fn finalize(
    paths: &EnginePaths<'_>,
    request: &Request,
    policy: &Policy,
    mut decision: Decision,
    cacheable: bool,
) -> Result<Decision, String> {
    if decision.allow {
        decision.permit = Some(permit::create(request, policy)?);
    }
    if cacheable {
        cache::store(paths.state_dir, request, policy, &decision, request.now)?;
    }
    audit::append(paths.state_dir, request, &decision)?;
    Ok(decision)
}
