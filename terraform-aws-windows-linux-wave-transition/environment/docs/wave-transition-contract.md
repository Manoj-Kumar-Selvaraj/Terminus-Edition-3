# Wave transition contract

Workloads in `/app/data/cmdb.json` get one private Linux replacement each. Disks in
`/app/data/disks.json` restore from snapshot lineage with stable Linux device names.
Dependencies in `/app/data/dependencies.json` plus maintenance windows decide cutover
order: a workload may hand off writer/DNS only after every dependency has a healthy
Linux guest and matching checksums.

Terraform must plan instances that are SSM-profiled, IMDSv2-required, private-IP
pinned, free of forbidden admin security groups listed in `/app/data/defaults.json`,
and must always include the required SSM security group from those defaults even when
the CMDB row omitted it. Root and data volumes use the inventory KMS key, gp3, and
termination protection. Data volumes restore from the listed snapshots. The rehearsal
engine materializes guests under `/app/var/wave/guests`, verifies
`/app/data/checksums.json`, and records handoff in `/app/output/cutover-journal.json`.
`/app/output/rehearsal-report.json` status is `READY` only when every workload handed
off without leaving dual writers or shared disk mounts. Reordering inventory maps must
not change semantics.
