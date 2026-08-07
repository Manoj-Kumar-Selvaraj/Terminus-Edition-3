Stage resource contracts (authoritative for deploy validation):

| stage | timeout_s | memory_mb | concurrency | actions |
| intake | 30 | 256 | 4 | logs:PutLogEvents, xray:PutTraceSegments |
| verify_manifest | 45 | 256 | 4 | s3:GetObject, kms:Verify, logs:PutLogEvents |
| acquire_lock | 20 | 128 | 8 | dynamodb:PutItem, dynamodb:GetItem, logs:PutLogEvents |
| fetch_inputs | 120 | 512 | 12 | s3:GetObject, logs:PutLogEvents |
| validate_inputs | 90 | 512 | 12 | s3:GetObject, logs:PutLogEvents |
| transform_records | 180 | 1024 | 8 | s3:GetObject, s3:PutObject, logs:PutLogEvents |
| precheck_ledger | 60 | 256 | 6 | dynamodb:GetItem, logs:PutLogEvents |
| write_ledger | 120 | 512 | 6 | dynamodb:PutItem, dynamodb:UpdateItem, logs:PutLogEvents |
| build_report | 90 | 512 | 4 | s3:PutObject, logs:PutLogEvents |
| notify_partner | 30 | 256 | 4 | events:PutEvents, logs:PutLogEvents |
| archive_batch | 60 | 256 | 4 | s3:GetObject, s3:PutObject, s3:DeleteObject, logs:PutLogEvents |
| release_lock | 20 | 128 | 8 | dynamodb:DeleteItem, logs:PutLogEvents |

Plan excerpt from the failed fleet showed a shared function name and `$LATEST` alias — that layout must not survive repair.
