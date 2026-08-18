# Org IPAM catalog

SQLite database `/app/data/ipam.sqlite` is built at image bake from `/app/docs/sql/schema.sql` and `/app/docs/sql/seed.sql`.

## Tables

`subnets(id TEXT PRIMARY KEY, account_id TEXT, az TEXT, tier TEXT, cidr TEXT)`

Eligible application subnets have `tier = 'private_app'` and `account_id` equal to the fleet account. IDs are unique. Availability zones must be unique among the subnets listed in `fleet_config.json`.

`images(ami_id TEXT PRIMARY KEY, owner_account_id TEXT, architecture TEXT, state TEXT, deprecated INTEGER)`

The approved `release_artifact.ami_id` must exist, be `available`, not deprecated, and match owner/architecture.

Controllers look up configured subnet IDs and the approved AMI in this catalog. Local JSON is not a substitute for a missing or ineligible IPAM row.
