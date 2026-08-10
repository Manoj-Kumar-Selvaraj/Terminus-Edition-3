Platform security, Monday.

CodeCommit IAM in the lab stand-in is not the same evaluator we run in prod. Alice can clone `ledger` at commit C, then push C to main from the office range without MFA. Reviewers are rubber-stamping and `merge` still makes a merge commit when main has moved. Pipeline `settle-prod` fired twice last night on the same head after two `deliver` calls.

Policies and attachments are the source of truth — do not invent a second allow list inside the CLI. I dumped last night's decisions under log/. Repos stay bare under var/repos. If you wipe var, recreate `ledger` through git; do not point origin at GitHub.
