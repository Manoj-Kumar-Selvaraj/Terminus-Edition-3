PRAGMA foreign_keys = ON;

BEGIN;

WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x + 1 FROM n WHERE x < 365)
INSERT INTO cycles(cycle_id,business_date,source,run_id,state,reconciliation_status,completion_status,started_at,reconciled_at,completed_at)
SELECT printf('H%04d',x),
       date('2025-08-09','+' || (x - 1) || ' days'),
       CASE x % 6
         WHEN 0 THEN 'CORP-ACH'
         WHEN 1 THEN 'TREASURY'
         WHEN 2 THEN 'VENDOR-BULK'
         WHEN 3 THEN 'PAYROLL'
         WHEN 4 THEN 'CARD-ACQ'
         ELSE 'RTGS'
       END,
       printf('RUN-%02d',1 + (x % 9)),
       'COMPLETED','BALANCED','COMPLETED',
       datetime('2025-08-09','+' || (x - 1) || ' days','+20 hours'),
       datetime('2025-08-09','+' || (x - 1) || ' days','+21 hours'),
       datetime('2025-08-09','+' || (x - 1) || ' days','+22 hours')
FROM n;

WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x + 1 FROM n WHERE x < 5000)
INSERT INTO accounts(account_id,status,balance_cents,currency,updated_at)
SELECT printf('A%06d',x),
       CASE
         WHEN x % 211 = 0 THEN 'CLOSED'
         WHEN x % 97 = 0 THEN 'BLOCKED'
         WHEN x % 53 = 0 THEN 'BLOCKED'
         ELSE 'ACTIVE'
       END,
       40000 + ((x * 104729 + 7919) % 9850000),
       CASE x % 11
         WHEN 0 THEN 'USD'
         WHEN 1 THEN 'EUR'
         WHEN 2 THEN 'GBP'
         WHEN 3 THEN 'SGD'
         WHEN 4 THEN 'AED'
         ELSE 'INR'
       END,
       datetime('2026-08-08','-' || (x % 180) || ' days')
FROM n;

WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x + 1 FROM n WHERE x < 19988)
INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose,received_seq)
SELECT x,
       printf('H%04d',1 + ((x - 1) % 365)),
       CASE x % 8
         WHEN 0 THEN printf('ACH-%08d',x)
         WHEN 1 THEN printf('BULK/%08d/%02d',x, x % 97)
         WHEN 2 THEN printf('API-%08d-%04d',x, (x * 17) % 10000)
         WHEN 3 THEN printf('MAN-%08d-%05d',x, (x * 7) % 100000)
         WHEN 4 THEN printf('WIRE-%08d',x)
         WHEN 5 THEN printf('CARD-%08d-%02d',x, x % 24)
         WHEN 6 THEN printf('RTGS/%08d',x)
         ELSE printf('PAYROLL-%08d',x)
       END,
       printf('A%06d',1 + ((x * 17 + 3) % 5000)),
       CASE x % 5
         WHEN 0 THEN printf('EXT-SG-%07d',x * 11 + 100)
         WHEN 1 THEN printf('EMP-%08d',x)
         WHEN 2 THEN printf('VND-%05d-%05d',x % 100000, x)
         WHEN 3 THEN printf('EXT-AE-%07d',x * 13 + 55)
         ELSE printf('INT-%06d',1 + ((x * 19 + 7) % 5000))
       END,
       CASE WHEN x % 5 = 0 OR x % 5 = 3 THEN NULL ELSE printf('A%06d',1 + ((x * 19 + 7) % 5000)) END,
       750 + x * 13 + ((x * 89) % 977),
       CASE x % 13
         WHEN 0 THEN 0
         WHEN 1 THEN 15
         WHEN 2 THEN 25
         WHEN 3 THEN 35
         WHEN 4 THEN 50
         WHEN 5 THEN 75
         WHEN 6 THEN 90
         WHEN 7 THEN 100
         WHEN 8 THEN 125
         WHEN 9 THEN 150
         WHEN 10 THEN 175
         WHEN 11 THEN 200
         ELSE 250
       END,
       CASE x % 17
         WHEN 0 THEN 0
         WHEN 1 THEN 4
         WHEN 2 THEN 8
         WHEN 3 THEN 12
         WHEN 4 THEN 18
         WHEN 5 THEN 25
         WHEN 6 THEN 32
         WHEN 7 THEN 40
         WHEN 8 THEN 48
         WHEN 9 THEN 55
         ELSE 70
       END,
       CASE x % 11
         WHEN 0 THEN 'USD'
         WHEN 1 THEN 'EUR'
         WHEN 2 THEN 'GBP'
         WHEN 3 THEN 'SGD'
         WHEN 4 THEN 'AED'
         ELSE 'INR'
       END,
       CASE x % 12
         WHEN 0 THEN 'PAYROLL'
         WHEN 1 THEN 'VENDOR'
         WHEN 2 THEN 'REFUND'
         WHEN 3 THEN 'TREASURY'
         WHEN 4 THEN 'RENT'
         WHEN 5 THEN 'CLAIM'
         WHEN 6 THEN 'TRANSFER'
         WHEN 7 THEN 'SALARY'
         WHEN 8 THEN 'DIVIDEND'
         WHEN 9 THEN 'TAX'
         WHEN 10 THEN 'INTEREST'
         ELSE 'SETTLEMENT'
       END,
       x * 10
FROM n;

INSERT INTO payment_history(source_ref,accepted_cycle_id,payer_account,beneficiary_ref,amount_cents,currency,purpose,status,recorded_at)
SELECT p.source_ref,
       CASE WHEN p.payment_id % 17 = 0 THEN NULL ELSE p.cycle_id END,
       p.payer_account,p.beneficiary_ref,p.amount_cents,p.currency,p.purpose,
       CASE WHEN p.payment_id % 17 = 0 THEN 'REJECTED' WHEN p.payment_id % 11 = 0 THEN 'ACCEPTED' ELSE 'COMPLETED' END,
       datetime('2025-08-09','+' || ((p.payment_id - 1) % 365) || ' days','+22 hours')
FROM payments p
WHERE p.cycle_id LIKE 'H%';

INSERT INTO payment_outcomes(payment_id,cycle_id,outcome,reason,execution_state,decided_at)
SELECT p.payment_id,p.cycle_id,
       CASE
         WHEN p.payment_id % 17 = 0 THEN 'REJECTED'
         WHEN p.payment_id % 23 = 0 THEN 'DUPLICATE'
         WHEN p.beneficiary_account IS NULL THEN 'SUCCESS_EXTERNAL'
         ELSE 'SUCCESS_INTERNAL'
       END,
       CASE
         WHEN p.payment_id % 17 = 0 THEN 'HISTORICAL_ACCOUNT_CONTROL'
         WHEN p.payment_id % 23 = 0 THEN 'HISTORICAL_REPLAY'
         WHEN p.beneficiary_account IS NULL THEN 'HISTORICAL_EXTERNAL'
         ELSE 'HISTORICAL_INTERNAL'
       END,
       'COMPLETED',
       datetime('2025-08-09','+' || ((p.payment_id - 1) % 365) || ' days','+21 hours')
FROM payments p
WHERE p.cycle_id LIKE 'H%';

INSERT INTO internal_postings(payment_id,cycle_id,payer_account,beneficiary_account,debit_cents,beneficiary_credit_cents,posted_at)
SELECT p.payment_id,p.cycle_id,p.payer_account,p.beneficiary_account,
       p.amount_cents+p.fee_cents+p.tax_cents,p.amount_cents,
       datetime('2025-08-09','+' || ((p.payment_id - 1) % 365) || ' days','+21 hours')
FROM payments p
JOIN payment_outcomes o ON o.payment_id=p.payment_id
WHERE p.cycle_id LIKE 'H%' AND o.outcome='SUCCESS_INTERNAL';

INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active,created_at,released_at)
SELECT p.payment_id,p.cycle_id,p.payer_account,p.amount_cents+p.fee_cents+p.tax_cents,0,
       datetime('2025-08-09','+' || ((p.payment_id - 1) % 365) || ' days','+21 hours'),
       datetime('2025-08-09','+' || ((p.payment_id - 1) % 365) || ' days','+22 hours')
FROM payments p
JOIN payment_outcomes o ON o.payment_id=p.payment_id
WHERE p.cycle_id LIKE 'H%' AND o.outcome='SUCCESS_EXTERNAL';

INSERT INTO clearing_items(payment_id,cycle_id,reservation_id,source_ref,amount_cents,currency,status,created_at)
SELECT p.payment_id,p.cycle_id,r.reservation_id,p.source_ref,p.amount_cents,p.currency,'ACKNOWLEDGED',
       datetime('2025-08-09','+' || ((p.payment_id - 1) % 365) || ' days','+21 hours')
FROM payments p
JOIN payment_outcomes o ON o.payment_id=p.payment_id
JOIN reservations r ON r.payment_id=p.payment_id
WHERE p.cycle_id LIKE 'H%' AND o.outcome='SUCCESS_EXTERNAL';

INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
SELECT p.payment_id,p.cycle_id,'D',CASE WHEN o.outcome='SUCCESS_INTERNAL' THEN 'CUSTOMER_CONTROL' ELSE 'CUSTOMER_RESERVED' END,
       p.amount_cents+p.fee_cents+p.tax_cents,
       datetime('2025-08-09','+' || ((p.payment_id-1)%365) || ' days','+21 hours')
FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id
WHERE p.cycle_id LIKE 'H%' AND o.outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL')
UNION ALL
SELECT p.payment_id,p.cycle_id,'C',CASE WHEN o.outcome='SUCCESS_INTERNAL' THEN 'BENEFICIARY_CONTROL' ELSE 'CLEARING_PAYABLE' END,
       p.amount_cents,
       datetime('2025-08-09','+' || ((p.payment_id-1)%365) || ' days','+21 hours')
FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id
WHERE p.cycle_id LIKE 'H%' AND o.outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL')
UNION ALL
SELECT p.payment_id,p.cycle_id,'C','FEE_INCOME',p.fee_cents,
       datetime('2025-08-09','+' || ((p.payment_id-1)%365) || ' days','+21 hours')
FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id
WHERE p.cycle_id LIKE 'H%' AND o.outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL')
UNION ALL
SELECT p.payment_id,p.cycle_id,'C','TAX_PAYABLE',p.tax_cents,
       datetime('2025-08-09','+' || ((p.payment_id-1)%365) || ' days','+21 hours')
FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id
WHERE p.cycle_id LIKE 'H%' AND o.outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL');

INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete,updated_at)
SELECT cycle_id,1,1,1,completed_at FROM cycles WHERE cycle_id LIKE 'H%';
INSERT INTO publication_batches(cycle_id,response_published,clearing_published,published_at)
SELECT cycle_id,1,1,completed_at FROM cycles WHERE cycle_id LIKE 'H%';
INSERT INTO success_authorizations(cycle_id,business_date,source,run_id,status,authorized_at)
SELECT cycle_id,business_date,source,run_id,'AUTHORIZED',completed_at FROM cycles WHERE cycle_id LIKE 'H%';
INSERT INTO delivery_events(cycle_id,channel,status,external_ref,recorded_at)
SELECT cycle_id,'SFTP','ACKNOWLEDGED','ACK-'||cycle_id,completed_at FROM cycles WHERE cycle_id LIKE 'H%';
INSERT INTO work_checkpoints(cycle_id,payment_id,stage,status,checkpoint_key,recorded_at)
SELECT cycle_id,NULL,'CONTROL','DONE',cycle_id||':CONTROL',completed_at FROM cycles WHERE cycle_id LIKE 'H%';
INSERT INTO audit_events(cycle_id,payment_id,event_type,event_key,event_detail,recorded_at)
SELECT o.cycle_id,o.payment_id,'PAYMENT_COMPLETED',o.cycle_id||':'||o.payment_id||':PAYMENT_COMPLETED',o.outcome,o.decided_at
FROM payment_outcomes o
WHERE o.cycle_id LIKE 'H%';

INSERT INTO payment_history(source_ref,accepted_cycle_id,payer_account,beneficiary_ref,amount_cents,currency,purpose,status,recorded_at) VALUES
('REPLAY-20260801-553901','H0358','A000110','A000111',76500,'INR','TRANSFER','COMPLETED','2026-08-01 22:14:11'),
('SIM-OLD-443200','H0357','A000112','A000113',88000,'INR','VENDOR','COMPLETED','2026-07-31 22:07:43');

INSERT INTO cycles(cycle_id,business_date,source,run_id,state,reconciliation_status,completion_status,started_at) VALUES('EOD-20260808-03','2026-08-08','CORP-ACH','RUN-03','OPEN','PENDING','PENDING','2026-08-08 22:11:02');
INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete,updated_at) VALUES('EOD-20260808-03',1,1,1,'2026-08-08 22:10:57');
UPDATE accounts SET status='ACTIVE',balance_cents=900000 WHERE account_id IN ('A000101','A000102','A000103','A000104','A000105','A000106','A000107','A000108','A000109','A000110','A000111','A000112','A000113','A000114');
UPDATE accounts SET status='BLOCKED',balance_cents=600000 WHERE account_id='A000194';
UPDATE accounts SET status='BLOCKED',balance_cents=550000 WHERE account_id='A000291';

INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose,received_seq) VALUES
(20001,'EOD-20260808-03','CORP-0808-INT-774291','A000101','A000102','A000102',125000,175,32,'INR','TRANSFER',10),
(20002,'EOD-20260808-03','CORP-0808-EXT-774292','A000103','EXT-SG-773',NULL,245000,225,41,'INR','VENDOR',20),
(20003,'EOD-20260808-03','CORP-0808-INT-774293','A000104','A000105','A000105',99000,125,25,'INR','TRANSFER',30),
(20004,'EOD-20260808-03','REPLAY-20260801-553901','A000110','A000111','A000111',76500,0,0,'INR','TRANSFER',40),
(20005,'EOD-20260808-03','SIM-NEW-443201','A000112','A000113','A000113',88000,0,0,'INR','VENDOR',50),
(20006,'EOD-20260808-03','CORP-0808-BLOCK-774294','A000194','EXT-UK-811',NULL,45000,75,18,'INR','VENDOR',60),
(20007,'EOD-20260808-03','CORP-0808-BENE-774295','A000114','A000291','A000291',62000,100,25,'INR','TRANSFER',70),
(20008,'EOD-20260808-03','CORP-0808-CAP-774296','A000106','EXT-AE-990',NULL,650000,175,40,'INR','TREASURY',80),
(20009,'EOD-20260808-03','CORP-0808-EXT-774297','A000106','EXT-SG-991',NULL,180000,125,25,'INR','VENDOR',15),
(20010,'EOD-20260808-03','CORP-0808-INT-774298','A000107','A000108','A000108',34000,0,0,'INR','PAYROLL',90),
(20011,'EOD-20260808-03','CORP-0808-EXT-774299','A000109','EXT-US-992',NULL,71500,50,12,'USD','REFUND',100),
(20012,'EOD-20260808-03','CORP-0808-INT-774300','A000110','A000111','A000111',42000,25,5,'INR','TRANSFER',110);

INSERT INTO payment_history(source_ref,accepted_cycle_id,payer_account,beneficiary_ref,amount_cents,currency,purpose,status,recorded_at) VALUES('CORP-0808-INT-774300','EOD-20260808-03','A000110','A000111',42000,'INR','TRANSFER','ACCEPTED','2026-08-08 22:15:44');
UPDATE accounts SET balance_cents=balance_cents-125207 WHERE account_id='A000101';
UPDATE accounts SET balance_cents=balance_cents+125000 WHERE account_id='A000102';
INSERT INTO internal_postings(payment_id,cycle_id,payer_account,beneficiary_account,debit_cents,beneficiary_credit_cents,posted_at) VALUES(20001,'EOD-20260808-03','A000101','A000102',125207,125000,'2026-08-08 22:16:51');
INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at) VALUES
(20001,'EOD-20260808-03','D','CUSTOMER_CONTROL',125207,'2026-08-08 22:16:51'),(20001,'EOD-20260808-03','C','BENEFICIARY_CONTROL',125000,'2026-08-08 22:16:51'),(20001,'EOD-20260808-03','C','FEE_INCOME',175,'2026-08-08 22:16:51'),(20001,'EOD-20260808-03','C','TAX_PAYABLE',32,'2026-08-08 22:16:51');
INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active,created_at) VALUES(20002,'EOD-20260808-03','A000103',245266,1,'2026-08-08 22:17:08'),(20009,'EOD-20260808-03','A000106',180150,1,'2026-08-08 22:14:39');
INSERT INTO clearing_items(payment_id,cycle_id,reservation_id,source_ref,amount_cents,currency,status,created_at) SELECT 20009,'EOD-20260808-03',reservation_id,'CORP-0808-EXT-774297',180000,'INR','READY','2026-08-08 22:14:48' FROM reservations WHERE payment_id=20009;
INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at) VALUES(20009,'EOD-20260808-03','D','CUSTOMER_RESERVED',180150,'2026-08-08 22:14:48'),(20009,'EOD-20260808-03','C','CLEARING_PAYABLE',180000,'2026-08-08 22:14:48'),(20009,'EOD-20260808-03','C','FEE_INCOME',125,'2026-08-08 22:14:48'),(20009,'EOD-20260808-03','C','TAX_PAYABLE',25,'2026-08-08 22:14:48');
INSERT INTO audit_events(cycle_id,payment_id,event_type,event_key,event_detail,recorded_at) VALUES
('EOD-20260808-03',20001,'INTERNAL_POSTED','EOD-20260808-03:20001:INTERNAL_POSTED','posting committed before host termination','2026-08-08 22:16:51'),('EOD-20260808-03',20002,'RESERVATION_CREATED','EOD-20260808-03:20002:RESERVATION_CREATED','reservation committed; clearing not reached','2026-08-08 22:17:08'),('EOD-20260808-03',20009,'RESERVATION_CREATED','EOD-20260808-03:20009:RESERVATION_CREATED','reservation from earlier pass','2026-08-08 22:14:39'),('EOD-20260808-03',20009,'CLEARING_CREATED','EOD-20260808-03:20009:CLEARING_CREATED','clearing already durable','2026-08-08 22:14:48');
INSERT INTO work_checkpoints(cycle_id,payment_id,stage,status,checkpoint_key,recorded_at) VALUES('EOD-20260808-03',20009,'EXECUTION','DONE','EOD-20260808-03:20009:EXECUTION','2026-08-08 22:14:49'),('EOD-20260808-03',20001,'EXECUTION','DONE','EOD-20260808-03:20001:EXECUTION','2026-08-08 22:16:52'),('EOD-20260808-03',20002,'EXECUTION','STARTED','EOD-20260808-03:20002:EXECUTION','2026-08-08 22:17:08');

COMMIT;
ANALYZE;
