use crate::model::Request;
use crate::policy::Policy;

pub trait AdmissionAdapter {
    fn kind(&self) -> &'static str;
    fn validate(&self, policy: &Policy, request: &Request) -> Result<(), String>;
}

struct PackageAdapter;
struct ContainerAdapter;
struct DependencyAdapter;

impl AdmissionAdapter for PackageAdapter {
    fn kind(&self) -> &'static str {
        "package"
    }

    fn validate(&self, policy: &Policy, request: &Request) -> Result<(), String> {
        if !policy.source_is_trusted(self.kind(), &request.source) {
            return Err("UNTRUSTED_SOURCE".to_string());
        }
        Ok(())
    }
}

impl AdmissionAdapter for ContainerAdapter {
    fn kind(&self) -> &'static str {
        "container"
    }

    fn validate(&self, policy: &Policy, request: &Request) -> Result<(), String> {
        if !policy.source_is_trusted(self.kind(), &request.source) {
            return Err("UNTRUSTED_SOURCE".to_string());
        }
        if policy.require_container_signature && !request.signed {
            return Err("CONTAINER_SIGNATURE_REQUIRED".to_string());
        }
        Ok(())
    }
}

impl AdmissionAdapter for DependencyAdapter {
    fn kind(&self) -> &'static str {
        "dependency"
    }

    fn validate(&self, policy: &Policy, request: &Request) -> Result<(), String> {
        if !policy.source_is_trusted(self.kind(), &request.source) {
            return Err("UNTRUSTED_SOURCE".to_string());
        }
        Ok(())
    }
}

pub fn validate(policy: &Policy, request: &Request) -> Result<(), String> {
    match request.kind.as_str() {
        "package" => PackageAdapter.validate(policy, request),
        "container" => ContainerAdapter.validate(policy, request),
        "dependency" => DependencyAdapter.validate(policy, request),
        _ => Err("UNSUPPORTED_ARTIFACT_KIND".to_string()),
    }
}
