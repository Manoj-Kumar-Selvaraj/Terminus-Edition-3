# Enterprise PII discovery plane verifier

Separate verifier for `enterprise-pii-discovery-plane`:

- Rebuilds submitted artifacts from `/app/enterprise-pii/scripts/build.sh`
- Drives the public HTTP API, `piictl`, and `pii-worker --scan-once`
- Uses hidden fixtures under `/tests/fixtures`
- Writes binary reward from `tests/test.sh`

The suite contains 30 F2P and 4 P2P behavioral tests named in `.terminus/designs/enterprise-pii-discovery-plane-test-map.json`.

Authorization cases use the optional `X-PII-Principal` request header with base64-encoded fixture principals from `/tests/fixtures/principals.json`.
