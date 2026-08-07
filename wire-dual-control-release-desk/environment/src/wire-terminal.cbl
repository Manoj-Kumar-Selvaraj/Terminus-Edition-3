       IDENTIFICATION DIVISION.
       PROGRAM-ID. WIRE-TERMINAL.
       AUTHOR. WIRE-SYSTEMS-GROUP.
       
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       REPOSITORY.
       
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       
       01 WS-ARGUMENT-COUNT             PIC 9(4) COMP-5 VALUE 0.
       01 WS-COMMAND                    PIC X(12) VALUE SPACES.
       01 WS-REVISION-TEXT              PIC X(16) VALUE SPACES.
       01 WS-AMOUNT-TEXT                PIC X(16) VALUE SPACES.
       01 WS-VALIDATION-CODE            PIC X(32) VALUE SPACES.
       01 WS-USAGE-VALID                PIC X VALUE "Y".
          88 USAGE-VALID                VALUE "Y".
          88 USAGE-INVALID              VALUE "N".
       01 WS-MUTATION                   PIC X VALUE "N".
          88 MUTATION-COMMAND           VALUE "Y".
       01 WS-TRANSACTION-DONE           PIC X VALUE "N".
          88 TRANSACTION-DONE           VALUE "Y".
       01 WS-SQL-FAILED                 PIC X VALUE "N".
          88 SQL-FAILED                 VALUE "Y".
       01 WS-RETRYABLE                  PIC X VALUE "N".
          88 RETRYABLE-ERROR            VALUE "Y".
       01 WS-REPLAYED                   PIC X VALUE "N".
          88 REQUEST-REPLAYED           VALUE "Y".
       01 WS-BUSINESS-FAILED            PIC X VALUE "N".
          88 BUSINESS-FAILED            VALUE "Y".
       01 WS-ATTEMPT                    PIC 9 VALUE 0.
       01 WS-EXIT-STATUS                PIC 9 VALUE 0.
       01 WS-BUSINESS-CODE              PIC X(24) VALUE SPACES.
       01 WS-PRIOR-STATE                PIC X(12) VALUE SPACES.
       01 WS-NEW-STATE                  PIC X(12) VALUE SPACES.
       01 WS-RESPONSE-WORK              PIC X(500) VALUE SPACES.
       01 WS-FINGERPRINT-WORK           PIC X(240) VALUE SPACES.
       01 WS-AUDIT-LINE                 PIC X(500) VALUE SPACES.
       01 WS-STATUS-LINE                PIC X(500) VALUE SPACES.
       01 WS-INDEX                      PIC 9(4) COMP-5 VALUE 0.
       01 WS-CHAR                       PIC X VALUE SPACE.
       01 WS-ALLOWED                    PIC X VALUE "N".
       
       01 WS-REVISION-EDIT              PIC 9(6).
       01 WS-AUDIT-EDIT                 PIC 9(10).
       01 WS-DEBIT-EDIT                 PIC 9(12).
       01 WS-CREDIT-EDIT                PIC 9(12).
       01 WS-AMOUNT-EDIT                PIC 9(12).
       
       EXEC SQL BEGIN DECLARE SECTION END-EXEC.
       01 H-DBNAME                      PIC X(80) VALUE SPACES.
       01 H-USERNAME                    PIC X(40) VALUE SPACES.
       01 H-PASSWORD                    PIC X(40) VALUE SPACES.
       01 H-REQUEST                     PIC X(24) VALUE SPACES.
       01 H-COMMAND                     PIC X(12) VALUE SPACES.
       01 H-WIRE                        PIC X(16) VALUE SPACES.
       01 H-DEBIT-ACCOUNT               PIC X(16) VALUE SPACES.
       01 H-CREDIT-ACCOUNT              PIC X(16) VALUE SPACES.
       01 H-INITIATOR                   PIC X(16) VALUE SPACES.
       01 H-APPROVER                    PIC X(16) VALUE SPACES.
       01 H-STATUS-APPROVER             PIC X(16) VALUE SPACES.
       01 H-EXPECTED-REVISION           PIC S9(9) COMP-3 VALUE 0.
       01 H-CURRENT-REVISION            PIC S9(9) COMP-3 VALUE 0.
       01 H-NEW-REVISION                PIC S9(9) COMP-3 VALUE 0.
       01 H-STATE                       PIC X(12) VALUE SPACES.
       01 H-AMOUNT                      PIC S9(18) COMP-3 VALUE 0.
       01 H-DEBIT-BALANCE               PIC S9(18) COMP-3 VALUE 0.
       01 H-CREDIT-BALANCE              PIC S9(18) COMP-3 VALUE 0.
       01 H-NEW-DEBIT-BALANCE           PIC S9(18) COMP-3 VALUE 0.
       01 H-NEW-CREDIT-BALANCE          PIC S9(18) COMP-3 VALUE 0.
       01 H-DISPLAY-DEBIT               PIC S9(18) COMP-3 VALUE 0.
       01 H-DISPLAY-CREDIT              PIC S9(18) COMP-3 VALUE 0.
       01 H-DEBIT-FROZEN                PIC S9(4) COMP-3 VALUE 0.
       01 H-CREDIT-FROZEN               PIC S9(4) COMP-3 VALUE 0.
       01 H-COUNT                       PIC S9(9) COMP-3 VALUE 0.
       01 H-LOCK-KEY                    PIC X(40) VALUE SPACES.
       01 H-FINGERPRINT                 PIC X(240) VALUE SPACES.
       01 H-STORED-FINGERPRINT          PIC X(240) VALUE SPACES.
       01 H-RESPONSE                    PIC X(500) VALUE SPACES.
       01 H-STORED-RESPONSE             PIC X(500) VALUE SPACES.
       01 H-AUDIT-SEQUENCE              PIC S9(18) COMP-3 VALUE 0.
       01 H-AUDIT-REQUEST               PIC X(24) VALUE SPACES.
       01 H-AUDIT-ACTION                PIC X(12) VALUE SPACES.
       01 H-AUDIT-PRIOR                 PIC X(12) VALUE SPACES.
       01 H-AUDIT-NEW                   PIC X(12) VALUE SPACES.
       01 H-AUDIT-REVISION              PIC S9(9) COMP-3 VALUE 0.
       EXEC SQL END DECLARE SECTION END-EXEC.
       
       EXEC SQL INCLUDE SQLCA END-EXEC.
       
       PROCEDURE DIVISION.
       
       MAIN.
           PERFORM INITIALIZE-RUNTIME
           PERFORM PARSE-COMMAND
           IF USAGE-INVALID
        PERFORM EMIT-USAGE-ERROR
        MOVE 2 TO RETURN-CODE
        GOBACK
           END-IF
       
           PERFORM CONNECT-DATABASE
           IF SQL-FAILED
        PERFORM EMIT-DATABASE-ERROR
        MOVE 3 TO RETURN-CODE
        GOBACK
           END-IF
       
           EVALUATE TRUE
        WHEN WS-COMMAND = "HEALTH"
            PERFORM PROCESS-HEALTH
        WHEN WS-COMMAND = "STATUS"
            PERFORM PROCESS-STATUS
        WHEN WS-COMMAND = "AUDIT"
            PERFORM PROCESS-AUDIT
        WHEN MUTATION-COMMAND
            PERFORM PROCESS-MUTATION
        WHEN OTHER
            SET USAGE-INVALID TO TRUE
            PERFORM EMIT-USAGE-ERROR
            MOVE 2 TO WS-EXIT-STATUS
           END-EVALUATE
       
           PERFORM DISCONNECT-DATABASE
           MOVE WS-EXIT-STATUS TO RETURN-CODE
           GOBACK.
       
       INITIALIZE-RUNTIME.
           INITIALIZE H-REQUEST H-COMMAND H-WIRE H-DEBIT-ACCOUNT
               H-CREDIT-ACCOUNT H-INITIATOR H-APPROVER
               H-STATUS-APPROVER H-FINGERPRINT H-RESPONSE
               H-STORED-FINGERPRINT H-STORED-RESPONSE
           MOVE "N" TO WS-MUTATION WS-TRANSACTION-DONE WS-SQL-FAILED
                WS-RETRYABLE WS-REPLAYED WS-BUSINESS-FAILED
           MOVE 0 TO WS-EXIT-STATUS
           ACCEPT H-DBNAME FROM ENVIRONMENT "WIRE_DB"
           ACCEPT H-USERNAME FROM ENVIRONMENT "WIRE_DB_USER"
           ACCEPT H-PASSWORD FROM ENVIRONMENT "WIRE_DB_PASSWORD"
           IF H-DBNAME = SPACES
        MOVE "wire@database:5432" TO H-DBNAME
           END-IF
           IF H-USERNAME = SPACES
        MOVE "wire_app" TO H-USERNAME
           END-IF
           IF H-PASSWORD = SPACES
        MOVE "wire_local" TO H-PASSWORD
           END-IF.
       
       PARSE-COMMAND.
           ACCEPT WS-ARGUMENT-COUNT FROM ARGUMENT-NUMBER
           IF WS-ARGUMENT-COUNT < 1
        SET USAGE-INVALID TO TRUE
        EXIT PARAGRAPH
           END-IF
           ACCEPT WS-COMMAND FROM ARGUMENT-VALUE
           MOVE FUNCTION UPPER-CASE(FUNCTION TRIM(WS-COMMAND))
             TO WS-COMMAND
           MOVE WS-COMMAND TO H-COMMAND
       
           EVALUATE WS-COMMAND
        WHEN "HEALTH"
            IF WS-ARGUMENT-COUNT NOT = 1
                SET USAGE-INVALID TO TRUE
            END-IF
        WHEN "STATUS"
            IF WS-ARGUMENT-COUNT NOT = 2
                SET USAGE-INVALID TO TRUE
            ELSE
                ACCEPT H-WIRE FROM ARGUMENT-VALUE
                PERFORM VALIDATE-WIRE-ID
            END-IF
        WHEN "AUDIT"
            IF WS-ARGUMENT-COUNT NOT = 2
                SET USAGE-INVALID TO TRUE
            ELSE
                ACCEPT H-WIRE FROM ARGUMENT-VALUE
                PERFORM VALIDATE-WIRE-ID
            END-IF
        WHEN "INITIATE"
            SET MUTATION-COMMAND TO TRUE
            IF WS-ARGUMENT-COUNT NOT = 7
                SET USAGE-INVALID TO TRUE
            ELSE
                ACCEPT H-REQUEST FROM ARGUMENT-VALUE
                ACCEPT H-WIRE FROM ARGUMENT-VALUE
                ACCEPT H-DEBIT-ACCOUNT FROM ARGUMENT-VALUE
                ACCEPT H-CREDIT-ACCOUNT FROM ARGUMENT-VALUE
                ACCEPT WS-AMOUNT-TEXT FROM ARGUMENT-VALUE
                ACCEPT H-INITIATOR FROM ARGUMENT-VALUE
                PERFORM VALIDATE-INITIATE-ARGUMENTS
            END-IF
        WHEN "APPROVE"
            SET MUTATION-COMMAND TO TRUE
            IF WS-ARGUMENT-COUNT NOT = 5
                SET USAGE-INVALID TO TRUE
            ELSE
                ACCEPT H-REQUEST FROM ARGUMENT-VALUE
                ACCEPT H-WIRE FROM ARGUMENT-VALUE
                ACCEPT WS-REVISION-TEXT FROM ARGUMENT-VALUE
                ACCEPT H-APPROVER FROM ARGUMENT-VALUE
                PERFORM VALIDATE-APPROVE-ARGUMENTS
            END-IF
        WHEN "RELEASE"
            SET MUTATION-COMMAND TO TRUE
            IF WS-ARGUMENT-COUNT NOT = 4
                SET USAGE-INVALID TO TRUE
            ELSE
                ACCEPT H-REQUEST FROM ARGUMENT-VALUE
                ACCEPT H-WIRE FROM ARGUMENT-VALUE
                ACCEPT WS-REVISION-TEXT FROM ARGUMENT-VALUE
                PERFORM VALIDATE-RELEASE-ARGUMENTS
            END-IF
        WHEN "CANCEL"
            SET MUTATION-COMMAND TO TRUE
            IF WS-ARGUMENT-COUNT NOT = 4
                SET USAGE-INVALID TO TRUE
            ELSE
                ACCEPT H-REQUEST FROM ARGUMENT-VALUE
                ACCEPT H-WIRE FROM ARGUMENT-VALUE
                ACCEPT WS-REVISION-TEXT FROM ARGUMENT-VALUE
                PERFORM VALIDATE-CANCEL-ARGUMENTS
            END-IF
        WHEN OTHER
            SET USAGE-INVALID TO TRUE
           END-EVALUATE
           IF USAGE-VALID AND MUTATION-COMMAND
        PERFORM BUILD-FINGERPRINT
           END-IF.
       
       BUILD-FINGERPRINT.
           MOVE SPACES TO WS-FINGERPRINT-WORK
           EVALUATE WS-COMMAND
        WHEN "INITIATE"
            STRING FUNCTION TRIM(WS-COMMAND) "|"
                   FUNCTION TRIM(H-REQUEST) "|"
                   FUNCTION TRIM(H-WIRE) "|"
                   FUNCTION TRIM(H-DEBIT-ACCOUNT) "|"
                   FUNCTION TRIM(H-CREDIT-ACCOUNT) "|"
                   FUNCTION TRIM(WS-AMOUNT-TEXT) "|"
                   FUNCTION TRIM(H-INITIATOR)
              INTO WS-FINGERPRINT-WORK
            END-STRING
        WHEN "APPROVE"
            STRING FUNCTION TRIM(WS-COMMAND) "|"
                   FUNCTION TRIM(H-REQUEST) "|"
                   FUNCTION TRIM(H-WIRE) "|"
                   FUNCTION TRIM(WS-REVISION-TEXT) "|"
                   FUNCTION TRIM(H-APPROVER)
              INTO WS-FINGERPRINT-WORK
            END-STRING
        WHEN OTHER
            STRING FUNCTION TRIM(WS-COMMAND) "|"
                   FUNCTION TRIM(H-REQUEST) "|"
                   FUNCTION TRIM(H-WIRE) "|"
                   FUNCTION TRIM(WS-REVISION-TEXT)
              INTO WS-FINGERPRINT-WORK
            END-STRING
           END-EVALUATE
           MOVE FUNCTION TRIM(WS-FINGERPRINT-WORK) TO H-FINGERPRINT.
       
       CONNECT-DATABASE.
           EXEC SQL
        CONNECT :H-USERNAME IDENTIFIED BY :H-PASSWORD
          USING :H-DBNAME
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
           END-IF.
       
       DISCONNECT-DATABASE.
           EXEC SQL ROLLBACK END-EXEC
           EXEC SQL DISCONNECT ALL END-EXEC.
       
       PROCESS-HEALTH.
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM information_schema.tables
         WHERE table_schema = 'public'
           AND table_name IN
               ('wire_request', 'ledger_entry', 'request_record',
                'audit_event')
           END-EXEC
           IF SQLCODE = 0 AND H-COUNT = 4
        DISPLAY "HEALTH|database=READY|schema=1"
        MOVE 0 TO WS-EXIT-STATUS
           ELSE
        DISPLAY "ERR|request=NONE|command=HEALTH|"
                "code=DATABASE_ERROR"
            UPON STDERR
        MOVE 3 TO WS-EXIT-STATUS
           END-IF.
       
       PROCESS-STATUS.
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM wire_request
         WHERE wire_id = :H-WIRE
           END-EXEC
           IF SQLCODE NOT = 0
        PERFORM EMIT-DATABASE-ERROR
        MOVE 3 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        DISPLAY "ERR|request=NONE|command=STATUS|"
                "code=UNKNOWN_WIRE"
        MOVE 1 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL
        SELECT revision, state, debit_account, credit_account,
               amount_cents, initiator_id,
               COALESCE(approver_id, 'NONE')
          INTO :H-CURRENT-REVISION, :H-STATE, :H-DEBIT-ACCOUNT,
               :H-CREDIT-ACCOUNT, :H-AMOUNT, :H-INITIATOR,
               :H-STATUS-APPROVER
          FROM wire_request
         WHERE wire_id = :H-WIRE
           END-EXEC
           IF SQLCODE NOT = 0
        PERFORM EMIT-DATABASE-ERROR
        MOVE 3 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
           MOVE H-CURRENT-REVISION TO WS-REVISION-EDIT
           MOVE H-AMOUNT TO WS-AMOUNT-EDIT
           MOVE SPACES TO WS-STATUS-LINE
           STRING "STATUS|wire=" FUNCTION TRIM(H-WIRE)
           "|revision=" WS-REVISION-EDIT
           "|state=" FUNCTION TRIM(H-STATE)
           "|debit-account=" FUNCTION TRIM(H-DEBIT-ACCOUNT)
           "|credit-account=" FUNCTION TRIM(H-CREDIT-ACCOUNT)
           "|amount=" WS-AMOUNT-EDIT
           "|initiator=" FUNCTION TRIM(H-INITIATOR)
           "|approver=" FUNCTION TRIM(H-STATUS-APPROVER)
             INTO WS-STATUS-LINE
           END-STRING
           DISPLAY FUNCTION TRIM(WS-STATUS-LINE TRAILING)
           MOVE 0 TO WS-EXIT-STATUS.
       
       PROCESS-AUDIT.
           EXEC SQL
               DECLARE AUDITCURSOR CURSOR FOR
               SELECT audit_sequence,
                      request_id,
                      action,
                      prior_state,
                      new_state,
                      resulting_revision
                 FROM audit_event
                WHERE wire_id = :H-WIRE
                ORDER BY audit_sequence
           END-EXEC
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM wire_request
         WHERE wire_id = :H-WIRE
           END-EXEC
           IF SQLCODE NOT = 0
        PERFORM EMIT-DATABASE-ERROR
        MOVE 3 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        DISPLAY "ERR|request=NONE|command=AUDIT|"
                "code=UNKNOWN_WIRE"
        MOVE 1 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL OPEN AUDITCURSOR END-EXEC
           IF SQLCODE NOT = 0
        PERFORM EMIT-DATABASE-ERROR
        MOVE 3 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
           PERFORM WITH TEST AFTER UNTIL SQLCODE NOT = 0
        EXEC SQL
                   FETCH AUDITCURSOR
             INTO :H-AUDIT-SEQUENCE,
                  :H-AUDIT-REQUEST,
                  :H-AUDIT-ACTION,
                  :H-AUDIT-PRIOR,
                  :H-AUDIT-NEW,
                  :H-AUDIT-REVISION
        END-EXEC
        IF SQLCODE = 0
            MOVE H-AUDIT-SEQUENCE TO WS-AUDIT-EDIT
            MOVE H-AUDIT-REVISION TO WS-REVISION-EDIT
            MOVE SPACES TO WS-AUDIT-LINE
            STRING "AUDIT|sequence=" WS-AUDIT-EDIT
                   "|request=" FUNCTION TRIM(H-AUDIT-REQUEST)
                   "|wire=" FUNCTION TRIM(H-WIRE)
                   "|action=" FUNCTION TRIM(H-AUDIT-ACTION)
                   "|from=" FUNCTION TRIM(H-AUDIT-PRIOR)
                   "|to=" FUNCTION TRIM(H-AUDIT-NEW)
                   "|revision=" WS-REVISION-EDIT
              INTO WS-AUDIT-LINE
            END-STRING
            DISPLAY FUNCTION TRIM(WS-AUDIT-LINE TRAILING)
        END-IF
           END-PERFORM
           EXEC SQL CLOSE AUDITCURSOR END-EXEC
           MOVE 0 TO WS-EXIT-STATUS.
       
       PROCESS-MUTATION.
           MOVE "N" TO WS-TRANSACTION-DONE
           PERFORM VARYING WS-ATTEMPT FROM 1 BY 1
        UNTIL TRANSACTION-DONE OR WS-ATTEMPT > 8
        MOVE "N" TO WS-SQL-FAILED WS-RETRYABLE
        PERFORM TRANSACTION-ATTEMPT
        IF SQL-FAILED
            IF SQLSTATE = "40001" OR SQLSTATE = "40P01"
                SET RETRYABLE-ERROR TO TRUE
            END-IF
            EXEC SQL ROLLBACK END-EXEC
            IF NOT RETRYABLE-ERROR
                SET TRANSACTION-DONE TO TRUE
                MOVE 3 TO WS-EXIT-STATUS
                PERFORM EMIT-DATABASE-ERROR
            END-IF
        END-IF
           END-PERFORM
           IF NOT TRANSACTION-DONE
        DISPLAY "ERR|request=" FUNCTION TRIM(H-REQUEST)
                "|command=" FUNCTION TRIM(H-COMMAND)
                "|code=RETRY_EXHAUSTED" UPON STDERR
        MOVE 3 TO WS-EXIT-STATUS
           END-IF.
       
       TRANSACTION-ATTEMPT.
           EXEC SQL INCLUDE "transaction-begin" END-EXEC.
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
       
           PERFORM HANDLE-REQUEST-IDENTITY
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
           IF REQUEST-REPLAYED
        EXEC SQL COMMIT END-EXEC
        IF SQLCODE NOT = 0
            SET SQL-FAILED TO TRUE
            EXIT PARAGRAPH
        END-IF
        DISPLAY FUNCTION TRIM(H-STORED-RESPONSE TRAILING)
        MOVE 0 TO WS-EXIT-STATUS
        SET TRANSACTION-DONE TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF BUSINESS-FAILED
        EXEC SQL ROLLBACK END-EXEC
        DISPLAY FUNCTION TRIM(H-RESPONSE TRAILING)
        MOVE 1 TO WS-EXIT-STATUS
        SET TRANSACTION-DONE TO TRUE
        EXIT PARAGRAPH
           END-IF
       
           EVALUATE WS-COMMAND
        WHEN "INITIATE"
            PERFORM APPLY-INITIATE
        WHEN "APPROVE"
            PERFORM APPLY-APPROVE
        WHEN "RELEASE"
            PERFORM APPLY-RELEASE
        WHEN "CANCEL"
            PERFORM APPLY-CANCEL
           END-EVALUATE
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
       
           IF BUSINESS-FAILED
        PERFORM RECORD-BUSINESS-REJECTION
           ELSE
        PERFORM RECORD-ACCEPTED-TRANSACTION
           END-IF
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL COMMIT END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           DISPLAY FUNCTION TRIM(H-RESPONSE TRAILING)
           IF BUSINESS-FAILED
        MOVE 1 TO WS-EXIT-STATUS
           ELSE
        MOVE 0 TO WS-EXIT-STATUS
           END-IF
           SET TRANSACTION-DONE TO TRUE.
       
       HANDLE-REQUEST-IDENTITY.
           MOVE "N" TO WS-REPLAYED WS-BUSINESS-FAILED
           EXEC SQL INCLUDE "request-identity" END-EXEC.
       
       APPLY-INITIATE.
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM wire_request
         WHERE wire_id = :H-WIRE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT > 0
        PERFORM SET-WIRE-EXISTS
        EXIT PARAGRAPH
           END-IF
       
           IF FUNCTION TRIM(H-DEBIT-ACCOUNT)
                = FUNCTION TRIM(H-CREDIT-ACCOUNT)
        PERFORM SET-INVALID-ACCOUNTS
        EXIT PARAGRAPH
           END-IF
       
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM wire_account
         WHERE account_id = :H-DEBIT-ACCOUNT
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        PERFORM SET-UNKNOWN-ACCOUNT
        EXIT PARAGRAPH
           END-IF
       
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM wire_account
         WHERE account_id = :H-CREDIT-ACCOUNT
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        PERFORM SET-UNKNOWN-ACCOUNT
        EXIT PARAGRAPH
           END-IF
       
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM wire_operator
         WHERE operator_id = :H-INITIATOR
           AND active = true
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        PERFORM SET-UNKNOWN-OPERATOR
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL
        SELECT balance_cents INTO :H-DISPLAY-DEBIT
          FROM wire_account
         WHERE account_id = :H-DEBIT-ACCOUNT
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        SELECT balance_cents INTO :H-DISPLAY-CREDIT
          FROM wire_account
         WHERE account_id = :H-CREDIT-ACCOUNT
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL
        INSERT INTO wire_request
            (wire_id, debit_account, credit_account, amount_cents,
             initiator_id, revision, state)
        VALUES
            (:H-WIRE, :H-DEBIT-ACCOUNT, :H-CREDIT-ACCOUNT,
             :H-AMOUNT, :H-INITIATOR, 1, 'INITIATED')
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           MOVE 1 TO H-NEW-REVISION
           MOVE "NONE" TO WS-PRIOR-STATE
           MOVE "INITIATED" TO WS-NEW-STATE.
       
       APPLY-APPROVE.
           PERFORM LOAD-WIRE-FOR-UPDATE
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           IF H-EXPECTED-REVISION NOT = H-CURRENT-REVISION
        PERFORM SET-STALE-REVISION
        EXIT PARAGRAPH
           END-IF
           IF FUNCTION TRIM(H-STATE) NOT = "INITIATED"
        PERFORM SET-INVALID-STATE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL INCLUDE "dual-control-check" END-EXEC.
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
       
           COMPUTE H-NEW-REVISION = H-CURRENT-REVISION + 1
           EXEC SQL
        UPDATE wire_request
           SET state = 'APPROVED',
               approver_id = :H-APPROVER,
               revision = :H-NEW-REVISION
         WHERE wire_id = :H-WIRE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           PERFORM LOAD-ACCOUNT-BALANCES
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
           MOVE H-DEBIT-BALANCE TO H-DISPLAY-DEBIT
           MOVE H-CREDIT-BALANCE TO H-DISPLAY-CREDIT
           MOVE "INITIATED" TO WS-PRIOR-STATE
           MOVE "APPROVED" TO WS-NEW-STATE.
       
       APPLY-RELEASE.
           PERFORM LOAD-WIRE-FOR-UPDATE
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           IF H-EXPECTED-REVISION NOT = H-CURRENT-REVISION
        PERFORM SET-STALE-REVISION
        EXIT PARAGRAPH
           END-IF
           IF FUNCTION TRIM(H-STATE) NOT = "APPROVED"
        PERFORM SET-INVALID-STATE
        EXIT PARAGRAPH
           END-IF
       
           PERFORM LOCK-AND-LOAD-ACCOUNTS
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL INCLUDE "freeze-gate" END-EXEC.
           IF BUSINESS-FAILED OR SQL-FAILED
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL INCLUDE "twin-post" END-EXEC.
           IF BUSINESS-FAILED OR SQL-FAILED
        EXIT PARAGRAPH
           END-IF
       
           COMPUTE H-NEW-REVISION = H-CURRENT-REVISION + 1
           EXEC SQL
        UPDATE wire_request
           SET state = 'RELEASED', revision = :H-NEW-REVISION
         WHERE wire_id = :H-WIRE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           MOVE "APPROVED" TO WS-PRIOR-STATE
           MOVE "RELEASED" TO WS-NEW-STATE.
       
       APPLY-CANCEL.
           PERFORM LOAD-WIRE-FOR-UPDATE
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           IF H-EXPECTED-REVISION NOT = H-CURRENT-REVISION
        PERFORM SET-STALE-REVISION
        EXIT PARAGRAPH
           END-IF
           IF FUNCTION TRIM(H-STATE) NOT = "INITIATED"
       AND FUNCTION TRIM(H-STATE) NOT = "APPROVED"
        PERFORM SET-INVALID-STATE
        EXIT PARAGRAPH
           END-IF
           MOVE H-STATE TO WS-PRIOR-STATE
           MOVE "CANCELLED" TO WS-NEW-STATE
           COMPUTE H-NEW-REVISION = H-CURRENT-REVISION + 1
           EXEC SQL
        UPDATE wire_request
           SET state = 'CANCELLED', revision = :H-NEW-REVISION
         WHERE wire_id = :H-WIRE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           PERFORM LOAD-ACCOUNT-BALANCES
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
           MOVE H-DEBIT-BALANCE TO H-DISPLAY-DEBIT
           MOVE H-CREDIT-BALANCE TO H-DISPLAY-CREDIT.
       
       LOAD-WIRE-FOR-UPDATE.
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM wire_request
         WHERE wire_id = :H-WIRE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        PERFORM SET-UNKNOWN-WIRE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        SELECT debit_account, credit_account, amount_cents,
               initiator_id, COALESCE(approver_id, 'NONE'),
               revision, state
          INTO :H-DEBIT-ACCOUNT, :H-CREDIT-ACCOUNT, :H-AMOUNT,
               :H-INITIATOR, :H-STATUS-APPROVER,
               :H-CURRENT-REVISION, :H-STATE
          FROM wire_request
         WHERE wire_id = :H-WIRE
           FOR UPDATE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
           END-IF.
       
       LOAD-ACCOUNT-BALANCES.
           EXEC SQL
        SELECT balance_cents INTO :H-DEBIT-BALANCE
          FROM wire_account
         WHERE account_id = :H-DEBIT-ACCOUNT
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        SELECT balance_cents INTO :H-CREDIT-BALANCE
          FROM wire_account
         WHERE account_id = :H-CREDIT-ACCOUNT
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
           END-IF.
       
       LOCK-AND-LOAD-ACCOUNTS.
           EXEC SQL
        SELECT balance_cents,
               CASE WHEN frozen THEN 1 ELSE 0 END
          INTO :H-DEBIT-BALANCE, :H-DEBIT-FROZEN
          FROM wire_account
         WHERE account_id = :H-DEBIT-ACCOUNT
           FOR UPDATE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        SELECT balance_cents,
               CASE WHEN frozen THEN 1 ELSE 0 END
          INTO :H-CREDIT-BALANCE, :H-CREDIT-FROZEN
          FROM wire_account
         WHERE account_id = :H-CREDIT-ACCOUNT
           FOR UPDATE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
           END-IF.
       
       RECORD-BUSINESS-REJECTION.
           PERFORM BUILD-ERROR-RESPONSE
           EXEC SQL
        INSERT INTO request_record
            (request_id, command_name, fingerprint,
             response_line, wire_id)
        VALUES
            (:H-REQUEST, :H-COMMAND, :H-FINGERPRINT, :H-RESPONSE,
             :H-WIRE)
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
           END-IF.
       
       RECORD-ACCEPTED-TRANSACTION.
           EXEC SQL
        SELECT next_value INTO :H-AUDIT-SEQUENCE
          FROM audit_counter
         WHERE singleton = true
           FOR UPDATE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        UPDATE audit_counter
           SET next_value = next_value + 1
         WHERE singleton = true
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           PERFORM BUILD-SUCCESS-RESPONSE
           EXEC SQL
        INSERT INTO request_record
            (request_id, command_name, fingerprint,
             response_line, wire_id)
        VALUES
            (:H-REQUEST, :H-COMMAND, :H-FINGERPRINT, :H-RESPONSE,
             :H-WIRE)
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        INSERT INTO audit_event
            (audit_sequence, request_id, wire_id, action,
             prior_state, new_state, resulting_revision)
        VALUES
            (:H-AUDIT-SEQUENCE, :H-REQUEST, :H-WIRE, :H-COMMAND,
             :WS-PRIOR-STATE, :WS-NEW-STATE, :H-NEW-REVISION)
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
           END-IF.
       
       BUILD-SUCCESS-RESPONSE.
           MOVE H-NEW-REVISION TO WS-REVISION-EDIT
           MOVE H-AUDIT-SEQUENCE TO WS-AUDIT-EDIT
           MOVE H-DISPLAY-DEBIT TO WS-DEBIT-EDIT
           MOVE H-DISPLAY-CREDIT TO WS-CREDIT-EDIT
           MOVE SPACES TO WS-RESPONSE-WORK H-RESPONSE
           STRING "OK|request=" FUNCTION TRIM(H-REQUEST)
           "|command=" FUNCTION TRIM(H-COMMAND)
           "|wire=" FUNCTION TRIM(H-WIRE)
           "|revision=" WS-REVISION-EDIT
           "|state=" FUNCTION TRIM(WS-NEW-STATE)
           "|debit=" WS-DEBIT-EDIT
           "|credit=" WS-CREDIT-EDIT
           "|audit=" WS-AUDIT-EDIT
             INTO WS-RESPONSE-WORK
           END-STRING
           MOVE FUNCTION TRIM(WS-RESPONSE-WORK) TO H-RESPONSE.
       
       BUILD-ERROR-RESPONSE.
           MOVE SPACES TO WS-RESPONSE-WORK H-RESPONSE
           STRING "ERR|request=" FUNCTION TRIM(H-REQUEST)
           "|command=" FUNCTION TRIM(H-COMMAND)
           "|code=" FUNCTION TRIM(WS-BUSINESS-CODE)
             INTO WS-RESPONSE-WORK
           END-STRING
           MOVE FUNCTION TRIM(WS-RESPONSE-WORK) TO H-RESPONSE.
       
       SET-WIRE-EXISTS.
           SET BUSINESS-FAILED TO TRUE
           MOVE "WIRE_EXISTS" TO WS-BUSINESS-CODE.
       
       SET-UNKNOWN-WIRE.
           SET BUSINESS-FAILED TO TRUE
           MOVE "UNKNOWN_WIRE" TO WS-BUSINESS-CODE.
       
       SET-UNKNOWN-ACCOUNT.
           SET BUSINESS-FAILED TO TRUE
           MOVE "UNKNOWN_ACCOUNT" TO WS-BUSINESS-CODE.
       
       SET-UNKNOWN-OPERATOR.
           SET BUSINESS-FAILED TO TRUE
           MOVE "UNKNOWN_OPERATOR" TO WS-BUSINESS-CODE.
       
       SET-SAME-OPERATOR.
           SET BUSINESS-FAILED TO TRUE
           MOVE "SAME_OPERATOR" TO WS-BUSINESS-CODE.
       
       SET-INVALID-ACCOUNTS.
           SET BUSINESS-FAILED TO TRUE
           MOVE "INVALID_ACCOUNTS" TO WS-BUSINESS-CODE.
       
       SET-STALE-REVISION.
           SET BUSINESS-FAILED TO TRUE
           MOVE "STALE_REVISION" TO WS-BUSINESS-CODE.
       
       SET-INVALID-STATE.
           SET BUSINESS-FAILED TO TRUE
           MOVE "INVALID_STATE" TO WS-BUSINESS-CODE.
       
       SET-ACCOUNT-FROZEN.
           SET BUSINESS-FAILED TO TRUE
           MOVE "ACCOUNT_FROZEN" TO WS-BUSINESS-CODE.
       
       SET-INSUFFICIENT-FUNDS.
           SET BUSINESS-FAILED TO TRUE
           MOVE "INSUFFICIENT_FUNDS" TO WS-BUSINESS-CODE.
       
       SET-REQUEST-CONFLICT.
           SET BUSINESS-FAILED TO TRUE
           MOVE "REQUEST_CONFLICT" TO WS-BUSINESS-CODE
           PERFORM BUILD-ERROR-RESPONSE.
       
       EMIT-USAGE-ERROR.
           DISPLAY "ERR|request=NONE|command=" FUNCTION TRIM(WS-COMMAND)
            "|code=USAGE" UPON STDERR.
       
       EMIT-DATABASE-ERROR.
           DISPLAY "ERR|request=" FUNCTION TRIM(H-REQUEST)
            "|command=" FUNCTION TRIM(H-COMMAND)
            "|code=DATABASE_ERROR" UPON STDERR.
       
       COPY "validation-rules.cpy".
       
       END PROGRAM WIRE-TERMINAL.
