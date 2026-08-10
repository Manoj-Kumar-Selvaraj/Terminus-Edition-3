# platform-sonar-ingress-token-bind

Internal platform MVP after the first apply: Jenkins on an EFS access point, SonarQube on Postgres, three public names on one ALB group. The second apply is supposed to interpolate a minted Sonar analysis token into JCasC. That bind did not converge.

The operator repairs Terraform/Helm/JCasC/Ingress/Ansible under `/app/platform/stack` and reloads the local control plane. Success is live state: token validates through the ingress hostname, siblings stay on one listener, ExternalDNS owns `platform.test` names, JDBC uses the RDS ternary address, Jenkins home survives reload, and Ansible stays on SSM.

Do not treat this as a plan-file or READY-digest lab. The scored artifact is the running bind.
