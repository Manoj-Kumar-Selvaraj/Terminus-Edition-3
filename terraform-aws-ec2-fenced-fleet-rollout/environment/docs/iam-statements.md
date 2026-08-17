# Fenced fleet IAM statements

Least-privilege instance role. Effect is Allow only. Wildcard actions are forbidden.

## SsmControlPlane

- Actions: `ec2messages:GetMessages`, `ssm:UpdateInstanceInformation`, `ssmmessages:CreateControlChannel`, `ssmmessages:OpenControlChannel`
- Resource: `*`
- Condition: `StringEquals` `aws:ResourceAccount` = configured account id

## ReadReleaseArtifact

- Actions: `s3:GetObject`
- Resource: configured artifact bucket ARN with `/*` (trim a trailing slash on the bucket ARN before appending)

## DecryptDataVolume

- Actions: `kms:Decrypt`
- Resource: sorted unique KMS key ARNs from `ebs_volumes`

## PublishPaymentsMetrics

- Actions: `cloudwatch:PutMetricData`
- Resource: `*`
- Condition: `StringEquals` `cloudwatch:namespace` = configured metric namespace
