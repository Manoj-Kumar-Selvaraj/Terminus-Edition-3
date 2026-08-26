# IRSA Trust & IAM Policy Technical Contract

IAM Roles for Service Accounts (IRSA) allow EKS pods to acquire fine-grained AWS IAM permissions.

## Security & Policy Rules

1. **Single-Subject Trust Binding**:
   - Each IRSA role must trust exactly ONE `system:serviceaccount:<namespace>:<name>` subject.
   - Example: `system:serviceaccount:kube-system:ebs-csi-controller-sa`.
   - Wildcard conditions, missing subjects, or multiple subjects are strictly rejected.

2. **Forbidden Subjects**:
   - Roles must NEVER trust `system:nodes` or wildcard node subjects.

3. **Policy Action Least-Privilege**:
   - Wildcard actions (`*` or service wildcards like `ebs:*`) are strictly forbidden.
   - IAM policies must grant only required actions on specific resource ARNs.

4. **Cross-Service Isolation**:
   - Each add-on (EBS CSI, Load Balancer Controller, Karpenter) must have a distinct, dedicated IAM Role ARN.
   - Sharing a single IAM Role ARN across multiple controllers is rejected as a cross-service trust violation.
