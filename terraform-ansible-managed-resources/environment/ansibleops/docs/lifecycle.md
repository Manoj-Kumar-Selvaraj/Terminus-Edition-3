# Terraform lifecycle contract

## Create

Validate the desired resource key and managed attributes, perform the required Ansible mutation, observe the resulting Linux object, then publish a stable ID and resulting Terraform state. No state transition is considered successful before the external mutation succeeds.

## Read / refresh

Read is side-effect free. It uses native Linux observation and never calls `ansible-playbook`. If the owned external object no longer exists, remove the resource from refreshed Terraform state so Terraform can plan recreation. Otherwise refresh observed values such as type, mode, owner/group, content digest, symlink target, account attributes, or cron schedule.

Read must preserve configured desired values while refreshing computed observations. Observed values use canonical representations so an unchanged object converges to a clean plan.

## Update

Keep the resource identity stable when only mutable properties change. Run the mutation before publishing the new applied state. If Ansible fails, times out, or is canceled, return an error and leave Terraform with the last successful state so the same desired update can be retried.

Content resources treat caller-supplied `source_digest` and template variables as desired configuration. Updating either must cause the required content mutation even when source/destination paths are unchanged.

## Delete

Deletion is scoped to the object's ownership key. Successful or already-absent deletion allows Terraform to remove the resource from state. A failed Ansible teardown must fail destroy rather than claim the object is gone.

Named line, block and cron resources may share their backing file/user with sibling resources. Their delete paths therefore remove only the named/selected owned entry. Symlink deletion removes the link path and never the target. User deletion removes the home directory only when `remove_home_on_destroy` is true.

## Idempotency

Repeated apply/refresh/plan against converged state performs no mutation. Map ordering, supplementary-group ordering, equivalent modes, and omitted versus explicit cron wildcards are normalized consistently. Resource-generated temporary playbooks do not survive success or failure paths.
