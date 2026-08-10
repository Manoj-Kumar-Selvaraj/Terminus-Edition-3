# Night shift — platform rebind

Minted a global analysis token in Sonar after `/api/system/status` went UP on the first apply. Put it in TFC as `sonarqube_token` (`ops/tfc-vars.json`) and re-applied.

Jenkins `/login` still answers. Quality-gate step comes back unauthorized. `sonar.platform.test` has been disappearing from the shared `platform-ingress` group every couple of minutes. ExternalDNS logs mention owner mismatch. JDBC URL in the Sonar values looks like it has `:5432` twice.

Do not open SSH on the ansible runner — that box is SSM only. Leave Jenkins home on the EFS access point; last time someone “fixed” JCasC by wiping the PVC we lost the seed jobs.

— Ravi
