# wiki-creation-counter-flap

Source: python-application (wiki-service FastAPI + Prometheus + K8s probes). Incident is Grafana creation-dashboard-678 going flat after a DB flap: live was retargeted at ready, pods restarted, process counters zeroed while COUNT(*) survived. Two replica scrapes.

Not a k8s cutover, not django HA checkout, not READY digest. Distinct from platform-sonar bind and jetstream.

Oracle: replace live/metrics/404/post_id; wikictl serve/flap/restore/report.
