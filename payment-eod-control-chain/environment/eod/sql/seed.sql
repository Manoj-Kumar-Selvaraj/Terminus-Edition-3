INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES
('CYCLE-2026-08-07','2026-08-07','CORP-ACH','RUN-001');

INSERT INTO accounts(account_id,status,balance_cents) VALUES
('A100','ACTIVE',250000),
('A200','ACTIVE',50000),
('A300','ACTIVE',300000),
('A400','ACTIVE',90000);

INSERT INTO payment_history(source_ref,payer_account,beneficiary_ref,amount_cents,currency,purpose,status) VALUES
('SRC-OLD-77','A100','B-EXT-1',25000,'INR','VENDOR','ACCEPTED'),
('SRC-REPLAY-1','A300','A400',12000,'INR','TRANSFER','COMPLETED');

INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose) VALUES
(1,'CYCLE-2026-08-07','SRC-INT-1','A100','A200','A200',30000,100,50,'INR','TRANSFER'),
(2,'CYCLE-2026-08-07','SRC-EXT-1','A300','B-EXT-1',NULL,25000,200,100,'INR','VENDOR'),
(3,'CYCLE-2026-08-07','SRC-REPLAY-1','A300','A400','A400',12000,0,0,'INR','TRANSFER'),
(4,'CYCLE-2026-08-07','SRC-EXT-2','A300','B-EXT-1',NULL,25000,200,100,'INR','VENDOR');

INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete)
VALUES ('CYCLE-2026-08-07',1,1,1);
