CREATE TRIGGER clearing_requires_active_reservation
BEFORE INSERT ON clearing_items
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM reservations r
            WHERE r.reservation_id = NEW.reservation_id
              AND r.payment_id = NEW.payment_id
              AND r.cycle_id = NEW.cycle_id
              AND r.active = 1
        )
        THEN RAISE(ABORT, 'active reservation required before clearing')
    END;
END;

CREATE TRIGGER balanced_cycle_enters_waiting_close
AFTER UPDATE OF reconciliation_status ON cycles
FOR EACH ROW
WHEN NEW.reconciliation_status = 'BALANCED'
 AND NEW.completion_status <> 'COMPLETED'
BEGIN
    UPDATE cycles
    SET state = 'RECONCILED',
        completion_status = 'WAITING'
    WHERE cycle_id = NEW.cycle_id;
END;

CREATE TRIGGER completed_cycle_requires_balanced_reconciliation
BEFORE UPDATE OF completion_status ON cycles
FOR EACH ROW
WHEN NEW.completion_status = 'COMPLETED'
BEGIN
    SELECT CASE
        WHEN NEW.reconciliation_status <> 'BALANCED'
        THEN RAISE(ABORT, 'balanced reconciliation required for completion')
    END;
END;

CREATE TRIGGER authorization_requires_completed_cycle
BEFORE INSERT ON success_authorizations
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM cycles c
            WHERE c.cycle_id = NEW.cycle_id
              AND c.completion_status = 'COMPLETED'
              AND c.reconciliation_status = 'BALANCED'
        )
        THEN RAISE(ABORT, 'completed cycle required for authorization')
    END;
END;
