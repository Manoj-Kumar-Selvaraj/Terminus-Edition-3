#!/bin/bash
set -euo pipefail
export PLATFORM_ROOT="${PLATFORM_ROOT:-/app/platform}"
export PYTHONPATH="${PLATFORM_ROOT}${PYTHONPATH:+:$PYTHONPATH}"
python3 - <<'PY'
from pathlib import Path
import os
root = Path(os.environ.get("PLATFORM_ROOT", "/app/platform"))

tf = (root / "stack/terraform/platform.tf").read_text(encoding="utf-8")
tf = tf.replace("posix_uid = 0", "posix_uid = 1000")
tf = tf.replace("posix_gid = 0", "posix_gid = 1000")
tf = tf.replace("ingress_ssh = true", "ingress_ssh = false")
tf = tf.replace("num_executors = 2", "num_executors = 0")
tf = tf.replace('sonarqube_secret_key = "token"', 'sonarqube_secret_key = "sonarqube-token"')
tf = tf.replace("postgresql_enabled = true", "postgresql_enabled = false")
tf = tf.replace(
    'jdbc_url = "jdbc:postgresql://platform-mvp-sonarqube.cluster.platform.test:5432:5432/sonarqube"',
    'jdbc_url = "jdbc:postgresql://platform-mvp-sonarqube.cluster.platform.test:5432/sonarqube"',
)
tf = tf.replace('jdbc_password_key = "db-password"', 'jdbc_password_key = "password"')
tf = tf.replace('policy = "upsert-only"', 'policy = "sync"')
tf = tf.replace('txt_owner_id = "platform-mvp"', 'txt_owner_id = "platform-mvp-dev"')
tf = tf.replace("domain_filters = []", 'domain_filters = ["platform.test"]')
(root / "stack/terraform/platform.tf").write_text(tf, encoding="utf-8")

sec = (root / "stack/k8s/secrets.yaml").read_text(encoding="utf-8")
sec = sec.replace("  token: \"\"", "  sonarqube-token: \"\"")
sec = sec.replace("  username: admin", "  artifactory-username: admin")
sec = sec.replace("  password: ops-artifactory-admin", "  artifactory-password: ops-artifactory-admin")
sec = sec.replace("  db-password: rds-sonar-pass", "  password: rds-sonar-pass")
(root / "stack/k8s/secrets.yaml").write_text(sec, encoding="utf-8")

ing = (root / "stack/k8s/ingress.yaml").read_text(encoding="utf-8")
ing = ing.replace(
    "    alb.ingress.kubernetes.io/group.name: jenkins-ingress\n    alb.ingress.kubernetes.io/healthcheck-path: /",
    "    alb.ingress.kubernetes.io/group.name: platform-ingress\n    alb.ingress.kubernetes.io/healthcheck-path: /login",
    1,
)
ing = ing.replace(
    "    alb.ingress.kubernetes.io/healthcheck-path: /login\n    alb.ingress.kubernetes.io/scheme: internet-facing\n    alb.ingress.kubernetes.io/target-type: ip\n    alb.ingress.kubernetes.io/listen-ports: '[{\"HTTPS\":443}]'\n    external-dns.alpha.kubernetes.io/hostname: sonar.platform.internal",
    "    alb.ingress.kubernetes.io/healthcheck-path: /api/system/status\n    alb.ingress.kubernetes.io/scheme: internet-facing\n    alb.ingress.kubernetes.io/target-type: ip\n    alb.ingress.kubernetes.io/listen-ports: '[{\"HTTPS\":443}]'\n    external-dns.alpha.kubernetes.io/hostname: sonar.platform.test",
    1,
)
ing = ing.replace(
    "    alb.ingress.kubernetes.io/healthcheck-path: /\n    alb.ingress.kubernetes.io/scheme: internet-facing\n    alb.ingress.kubernetes.io/target-type: ip\n    alb.ingress.kubernetes.io/listen-ports: '[{\"HTTPS\":443}]'\n    external-dns.alpha.kubernetes.io/hostname: artifactory.platform.test",
    "    alb.ingress.kubernetes.io/healthcheck-path: /artifactory/api/system/ping\n    alb.ingress.kubernetes.io/scheme: internet-facing\n    alb.ingress.kubernetes.io/target-type: ip\n    alb.ingress.kubernetes.io/listen-ports: '[{\"HTTPS\":443}]'\n    external-dns.alpha.kubernetes.io/hostname: artifactory.platform.test",
    1,
)
(root / "stack/k8s/ingress.yaml").write_text(ing, encoding="utf-8")

wl = (root / "stack/k8s/workloads.yaml").read_text(encoding="utf-8")
wl = wl.replace("reclaimPolicy: Delete", "reclaimPolicy: Retain")
wl = wl.replace(
    "  name: jenkins\n  namespace: jenkins\nspec:\n  template:\n    spec:\n      nodeSelector:\n        role: platform-exec\n      tolerations: []",
    "  name: jenkins\n  namespace: jenkins\nspec:\n  template:\n    spec:\n      nodeSelector:\n        role: platform-control\n      tolerations:\n        - key: platform-control\n          value: \"true\"\n          effect: NoSchedule",
    1,
)
wl = wl.replace(
    "  name: artifactory-data\n  namespace: artifactory\n  annotations:\n    platform/mount-path: /var/jenkins_home",
    "  name: artifactory-data\n  namespace: artifactory\n  annotations:\n    platform/mount-path: /var/opt/jfrog/artifactory",
    1,
)
(root / "stack/k8s/workloads.yaml").write_text(wl, encoding="utf-8")

casc = """jenkins:
  systemMessage: Platform MVP Jenkins
  numExecutors: 0
  mode: EXCLUSIVE
  globalNodeProperties:
    - envVars:
        ANSIBLE_RUNNER_ID: i-0a1b2c3d4e5f67890
        SONAR_URL: https://sonar.platform.test
credentials:
  system:
    domainCredentials:
      - credentials:
          - string:
              id: sonarqube-token
              secret: "${sonarqube-token}"
unclassified:
  sonarGlobalConfiguration:
    buildWrapperEnabled: true
    installations:
      - name: SonarQube
        serverUrl: https://sonar.platform.test
        credentialsId: sonarqube-token
"""
(root / "stack/jenkins/casc.yaml").write_text(casc, encoding="utf-8")

aws_inv = """all:
  vars:
    ansible_connection: aws_ssm
    ansible_aws_ssm_region: us-east-1
    ansible_aws_ssm_bucket_name: platform-ssm
  children:
    runners:
      hosts:
        runner:
          ansible_aws_ssm_instance_id: i-0a1b2c3d4e5f67890
"""
(root / "stack/ansible/inventories/aws/hosts.yml").write_text(aws_inv, encoding="utf-8")
print("stack patched")
PY
chmod +x "${PLATFORM_ROOT}/scripts/reload" "${PLATFORM_ROOT}/scripts/validate.sh"
"${PLATFORM_ROOT}/scripts/reload"
"${PLATFORM_ROOT}/scripts/reload"
"${PLATFORM_ROOT}/scripts/validate.sh"
