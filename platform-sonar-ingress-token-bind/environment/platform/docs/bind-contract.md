# Platform bind contract

Domain is `platform.test`. Public hosts are `jenkins.platform.test`, `sonar.platform.test`, and `artifactory.platform.test`. Cluster name / ExternalDNS `txtOwnerId` is `platform-mvp-dev`.

## Ingress

All three Ingress objects use class `alb`, `scheme=internet-facing`, `target-type=ip`, listen HTTPS:443, and `alb.ingress.kubernetes.io/group.name=platform-ingress`. They share one TLS listener. Splitting `group.name` per host is not allowed.

Healthcheck paths:

| Host | Path |
| --- | --- |
| jenkins.platform.test | `/login` |
| sonar.platform.test | `/api/system/status` |
| artifactory.platform.test | `/artifactory/api/system/ping` |

`external-dns.alpha.kubernetes.io/hostname` must equal the Ingress host. `policy=sync`. `domainFilters` includes `platform.test`. Sync deletes names the owner does not claim.

## Secrets and JCasC

| Secret | Namespace | Keys |
| --- | --- | --- |
| jenkins-sonarqube-token | jenkins | `sonarqube-token` |
| jenkins-artifactory-credentials | jenkins | `artifactory-username`, `artifactory-password` |
| jenkins-admin-credentials | jenkins | `jenkins-admin-user`, `jenkins-admin-password` |
| sonarqube-db-credentials | sonarqube | `password` |

Helm `additionalExistingSecrets[].keyName` matches those keys. JCasC string credential id is `sonarqube-token`. Installation name is `SonarQube`. `serverUrl` is `https://sonar.platform.test`. Do not point Jenkins at the RDS hostname.

The analysis token value comes from `/app/platform/ops/tfc-vars.json` field `sonarqube_token`. Reload interpolates it into the secret; it must not mint a replacement token. Empty token fails bind.

## JDBC ternary

`local.sonarqube_rds_address`:

1. `enable_dr_restore` → restored instance address
2. else non-empty `rds_endpoint_override`
3. else primary `address` (host only, never `endpoint` which already includes `:port`)

URL: `jdbc:postgresql://<address>:5432/sonarqube`. `postgresql.enabled=false`. Secret key `password`.

Sonar `/api/system/status` is `UP` only on a valid identity. Bind is refused while status is not `UP`.

## Persistence and schedule

Jenkins home is `/app/platform/var/efs/jenkins-home`, access-point path `/jenkins-home`, uid/gid 1000, StorageClass reclaim `Retain`. Artifactory data is `/app/platform/var/efs/artifactory-data`. Controller `numExecutors=0`, `nodeSelector.role=platform-control`, toleration `platform-control=true:NoSchedule`.

A second reload keeps the same token and existing files under Jenkins home.

## Ansible runner

AWS inventory: `ansible_connection=aws_ssm`. Jenkins global env `ANSIBLE_RUNNER_ID` is the runner instance id from terraform. Document name `AWS-RunShellScript`. Playbooks live under `/opt/ansible`. SSH connection, port 22 on the runner SG, and the on-prem inventory are not allowed for AWS deploys.
