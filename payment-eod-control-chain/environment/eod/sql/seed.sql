INSERT INTO cycles(cycle_id,business_date,source,run_id,state,reconciliation_status,completion_status)
VALUES ('CYCLE-DEMO','2026-08-08','CORP-ACH','RUN-DEMO','OPEN','PENDING','PENDING');

INSERT INTO accounts(account_id,status,balance_cents,currency) VALUES
('A100','ACTIVE',250000,'INR'),
('A200','ACTIVE',50000,'INR'),
('A300','ACTIVE',300000,'INR'),
('A400','ACTIVE',90000,'INR'),
('A500','BLOCKED',70000,'INR');

INSERT INTO payment_history(
    source_ref,accepted_cycle_id,payer_account,beneficiary_ref,amount_cents,currency,purpose,status
) VALUES
('SRC-OLD-REPLAY',NULL,'A300','A400',12000,'INR','TRANSFER','COMPLETED'),
('SRC-OLD-EXT',NULL,'A300','B-EXT-OLD',25000,'INR','VENDOR','ACCEPTED');

INSERT INTO payments(
    payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,
    amount_cents,fee_cents,tax_cents,currency,purpose,received_seq
) VALUES
(1,'CYCLE-DEMO','SRC-INT-1','A100','A200','A200',30000,100,50,'INR','TRANSFER',10),
(2,'CYCLE-DEMO','SRC-EXT-1','A300','B-EXT-1',NULL,25000,200,100,'INR','VENDOR',20),
(3,'CYCLE-DEMO','SRC-OLD-REPLAY','A300','A400','A400',12000,0,0,'INR','TRANSFER',30),
(4,'CYCLE-DEMO','SRC-EXT-2','A300','B-EXT-1',NULL,25000,200,100,'INR','VENDOR',40);

INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete)
VALUES ('CYCLE-DEMO',1,1,1);
