Shift notes 2026-08-16

Replica slot epoch 3 is current. After the bounce we still have an open WAL txn with no COMMIT (sku s-crash-pending). Do not treat that as catalog inventory.

CDC has to come off the WAL. A heap dump after the crash includes that pending insert and the replica apply then either duplicates LSNs or moves confirmed_lsn onto junk.

Frozen tenants (status FROZEN) are still in the heap from before the freeze. New offers/holds for those tenants have to fail closed.

Replica is only caught up through the sku batch. Offers and holds are still primary-only. Apply has to keep epoch 3 and not rewind confirmed_lsn.

--reset-output is for /app/catalog/out, not the WAL.
