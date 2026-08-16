Platform security, Monday.

CodeCommit IAM in the lab stand-in is not the same evaluator we run in prod. Alice can clone `ledger` at commit C, then push C to main from the office range without MFA. Reviewers are rubber-stamping and `merge` still makes a merge commit when main has moved. Pipeline `settle-prod` fired twice last night on the same head after two `deliver` calls.

Policies under policies/ and attachments in ops/principals.json are the evaluated source of truth for who may act. I dumped last night's decisions under log/. Repos stay bare under var/repos. If you wipe var, recreate `ledger` through git; do not point origin at GitHub.
