       IDENTIFICATION DIVISION.
       PROGRAM-ID. WORKSHOP-TERMINAL.
       AUTHOR. WORKSHOP-SYSTEMS-GROUP.
       
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       REPOSITORY.
       
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       
       01 WS-ARGUMENT-COUNT             PIC 9(4) COMP-5 VALUE 0.
       01 WS-COMMAND                    PIC X(12) VALUE SPACES.
       01 WS-REVISION-TEXT              PIC X(12) VALUE SPACES.
       01 WS-PRIORITY-TEXT              PIC X(12) VALUE SPACES.
       01 WS-START-TEXT                 PIC X(12) VALUE SPACES.
       01 WS-END-TEXT                   PIC X(12) VALUE SPACES.
       01 WS-VALIDATION-CODE            PIC X(24) VALUE SPACES.
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
       01 WS-BOOKING-OUT                PIC X(32) VALUE "NONE".
       01 WS-RESPONSE-WORK              PIC X(500) VALUE SPACES.
       01 WS-RESPONSE-REPLAY            PIC X(500) VALUE SPACES.
       01 WS-FINGERPRINT-WORK           PIC X(240) VALUE SPACES.
       01 WS-AUDIT-LINE                 PIC X(500) VALUE SPACES.
       01 WS-STATUS-LINE                PIC X(500) VALUE SPACES.
       01 WS-SCHEMA-VERSION             PIC 9 VALUE 0.
       01 WS-INDEX                      PIC 9(4) COMP-5 VALUE 0.
       01 WS-CHAR                       PIC X VALUE SPACE.
       01 WS-ALLOWED                    PIC X VALUE "N".
       01 WS-POLICY-ALLOWED             PIC X VALUE "N".
       01 WS-POLICY-MAX-DURATION        PIC S9(9) COMP-3 VALUE 0.
       
       01 WS-REVISION-EDIT              PIC 9(6).
       01 WS-AUDIT-EDIT                 PIC 9(10).
       01 WS-START-EDIT                 PIC 9(6).
       01 WS-END-EDIT                   PIC 9(6).
       01 WS-PRIORITY-EDIT              PIC 9.
       
       EXEC SQL BEGIN DECLARE SECTION END-EXEC.
       01 H-DBNAME                      PIC X(80) VALUE SPACES.
       01 H-USERNAME                    PIC X(40) VALUE SPACES.
       01 H-PASSWORD                    PIC X(40) VALUE SPACES.
       01 H-REQUEST                     PIC X(24) VALUE SPACES.
       01 H-COMMAND                     PIC X(12) VALUE SPACES.
       01 H-ORDER                       PIC X(16) VALUE SPACES.
       01 H-CLASS                       PIC X(16) VALUE SPACES.
       01 H-PRIORITY                    PIC S9(4) COMP-3 VALUE 0.
       01 H-EXPECTED-REVISION           PIC S9(9) COMP-3 VALUE 0.
       01 H-CURRENT-REVISION            PIC S9(9) COMP-3 VALUE 0.
       01 H-NEW-REVISION                PIC S9(9) COMP-3 VALUE 0.
       01 H-STATE                       PIC X(12) VALUE SPACES.
       01 H-BAY                         PIC X(8) VALUE SPACES.
       01 H-BAY-CAPABILITY              PIC X(16) VALUE SPACES.
       01 H-BAY-ACTIVE                  PIC S9(4) COMP-3 VALUE 0.
       01 H-TECHNICIAN                  PIC X(8) VALUE SPACES.
       01 H-TECH-CERTIFICATION          PIC X(16) VALUE SPACES.
       01 H-TECH-ACTIVE                 PIC S9(4) COMP-3 VALUE 0.
       01 H-START-TICK                  PIC S9(9) COMP-3 VALUE 0.
       01 H-END-TICK                    PIC S9(9) COMP-3 VALUE 0.
       01 H-BOOKING                     PIC X(20) VALUE SPACES.
       01 H-BOOKING-REVISION            PIC S9(9) COMP-3 VALUE 0.
       01 H-COUNT                       PIC S9(9) COMP-3 VALUE 0.
       01 H-LOCK-KEY                    PIC X(40) VALUE SPACES.
       01 H-POLICY-ID                   PIC X(16) VALUE SPACES.
       01 H-SHIFT-CODE                  PIC X VALUE SPACE.
       01 H-SUPERVISION-LEVEL           PIC S9(4) COMP-3 VALUE 0.
       01 H-CAPACITY-PERCENT            PIC S9(4) COMP-3 VALUE 0.
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
       01 H-STATUS-BOOKING              PIC X(20) VALUE SPACES.
       01 H-STATUS-BAY                  PIC X(8) VALUE SPACES.
       01 H-STATUS-TECH                 PIC X(8) VALUE SPACES.
       01 H-STATUS-START                PIC S9(9) COMP-3 VALUE 0.
       01 H-STATUS-END                  PIC S9(9) COMP-3 VALUE 0.
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
           INITIALIZE H-REQUEST H-COMMAND H-ORDER H-CLASS H-BAY
               H-TECHNICIAN H-BOOKING H-FINGERPRINT H-RESPONSE
               H-STORED-FINGERPRINT H-STORED-RESPONSE
           MOVE "N" TO WS-MUTATION WS-TRANSACTION-DONE WS-SQL-FAILED
                WS-RETRYABLE WS-REPLAYED WS-BUSINESS-FAILED
           MOVE 0 TO WS-EXIT-STATUS
           ACCEPT H-DBNAME FROM ENVIRONMENT "WORKSHOP_DB"
           ACCEPT H-USERNAME FROM ENVIRONMENT "WORKSHOP_DB_USER"
           ACCEPT H-PASSWORD FROM ENVIRONMENT "WORKSHOP_DB_PASSWORD"
           IF H-DBNAME = SPACES
        MOVE "workshop@database:5432" TO H-DBNAME
           END-IF
           IF H-USERNAME = SPACES
        MOVE "workshop_app" TO H-USERNAME
           END-IF
           IF H-PASSWORD = SPACES
        MOVE "workshop_local" TO H-PASSWORD
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
                ACCEPT H-ORDER FROM ARGUMENT-VALUE
                PERFORM VALIDATE-ORDER-ID
            END-IF
        WHEN "AUDIT"
            IF WS-ARGUMENT-COUNT NOT = 2
                SET USAGE-INVALID TO TRUE
            ELSE
                ACCEPT H-ORDER FROM ARGUMENT-VALUE
                PERFORM VALIDATE-ORDER-ID
            END-IF
        WHEN "OPEN"
            SET MUTATION-COMMAND TO TRUE
            IF WS-ARGUMENT-COUNT NOT = 5
                SET USAGE-INVALID TO TRUE
            ELSE
                ACCEPT H-REQUEST FROM ARGUMENT-VALUE
                ACCEPT H-ORDER FROM ARGUMENT-VALUE
                ACCEPT H-CLASS FROM ARGUMENT-VALUE
                ACCEPT WS-PRIORITY-TEXT FROM ARGUMENT-VALUE
                PERFORM VALIDATE-OPEN-ARGUMENTS
            END-IF
        WHEN "RESERVE"
            SET MUTATION-COMMAND TO TRUE
            PERFORM PARSE-SCHEDULE-COMMAND
        WHEN "MOVE"
            SET MUTATION-COMMAND TO TRUE
            PERFORM PARSE-SCHEDULE-COMMAND
        WHEN "START"
            SET MUTATION-COMMAND TO TRUE
            PERFORM PARSE-TRANSITION-COMMAND
        WHEN "COMPLETE"
            SET MUTATION-COMMAND TO TRUE
            PERFORM PARSE-TRANSITION-COMMAND
        WHEN "CANCEL"
            SET MUTATION-COMMAND TO TRUE
            PERFORM PARSE-TRANSITION-COMMAND
        WHEN OTHER
            SET USAGE-INVALID TO TRUE
           END-EVALUATE
           IF USAGE-VALID AND MUTATION-COMMAND
        PERFORM BUILD-FINGERPRINT
           END-IF.
       
       PARSE-SCHEDULE-COMMAND.
           IF WS-ARGUMENT-COUNT NOT = 8
        SET USAGE-INVALID TO TRUE
        EXIT PARAGRAPH
           END-IF
           ACCEPT H-REQUEST FROM ARGUMENT-VALUE
           ACCEPT H-ORDER FROM ARGUMENT-VALUE
           ACCEPT WS-REVISION-TEXT FROM ARGUMENT-VALUE
           ACCEPT H-BAY FROM ARGUMENT-VALUE
           ACCEPT H-TECHNICIAN FROM ARGUMENT-VALUE
           ACCEPT WS-START-TEXT FROM ARGUMENT-VALUE
           ACCEPT WS-END-TEXT FROM ARGUMENT-VALUE
           PERFORM VALIDATE-SCHEDULE-ARGUMENTS.
       
       PARSE-TRANSITION-COMMAND.
           IF WS-ARGUMENT-COUNT NOT = 4
        SET USAGE-INVALID TO TRUE
        EXIT PARAGRAPH
           END-IF
           ACCEPT H-REQUEST FROM ARGUMENT-VALUE
           ACCEPT H-ORDER FROM ARGUMENT-VALUE
           ACCEPT WS-REVISION-TEXT FROM ARGUMENT-VALUE
           PERFORM VALIDATE-TRANSITION-ARGUMENTS.
       
       BUILD-FINGERPRINT.
           MOVE SPACES TO WS-FINGERPRINT-WORK
           EVALUATE WS-COMMAND
        WHEN "OPEN"
            STRING FUNCTION TRIM(WS-COMMAND) "|"
                   FUNCTION TRIM(H-REQUEST) "|"
                   FUNCTION TRIM(H-ORDER) "|"
                   FUNCTION TRIM(H-CLASS) "|"
                   FUNCTION TRIM(WS-PRIORITY-TEXT)
              INTO WS-FINGERPRINT-WORK
            END-STRING
        WHEN "RESERVE"
        WHEN "MOVE"
            STRING FUNCTION TRIM(WS-COMMAND) "|"
                   FUNCTION TRIM(H-REQUEST) "|"
                   FUNCTION TRIM(H-ORDER) "|"
                   FUNCTION TRIM(WS-REVISION-TEXT) "|"
                   FUNCTION TRIM(H-BAY) "|"
                   FUNCTION TRIM(H-TECHNICIAN) "|"
                   FUNCTION TRIM(WS-START-TEXT) "|"
                   FUNCTION TRIM(WS-END-TEXT)
              INTO WS-FINGERPRINT-WORK
            END-STRING
        WHEN OTHER
            STRING FUNCTION TRIM(WS-COMMAND) "|"
                   FUNCTION TRIM(H-REQUEST) "|"
                   FUNCTION TRIM(H-ORDER) "|"
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
               ('work_order', 'booking', 'request_record',
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
          FROM work_order
         WHERE work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        PERFORM EMIT-DATABASE-ERROR
        MOVE 3 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        DISPLAY "ERR|request=NONE|command=STATUS|"
                "code=UNKNOWN_ORDER"
        MOVE 1 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL
        SELECT w.equipment_class,
               w.priority,
               w.revision,
               w.state,
               COALESCE(b.booking_id, 'NONE'),
               COALESCE(b.bay_id, 'NONE'),
               COALESCE(b.technician_id, 'NONE'),
               COALESCE(b.start_tick, 0),
               COALESCE(b.end_tick, 0)
          INTO :H-CLASS,
               :H-PRIORITY,
               :H-CURRENT-REVISION,
               :H-STATE,
               :H-STATUS-BOOKING,
               :H-STATUS-BAY,
               :H-STATUS-TECH,
               :H-STATUS-START,
               :H-STATUS-END
          FROM work_order w
          LEFT JOIN booking b
            ON b.work_order_id = w.work_order_id
           AND b.state IN ('RESERVED', 'STARTED')
         WHERE w.work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        PERFORM EMIT-DATABASE-ERROR
        MOVE 3 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
           MOVE H-CURRENT-REVISION TO WS-REVISION-EDIT
           MOVE H-PRIORITY TO WS-PRIORITY-EDIT
           MOVE H-STATUS-START TO WS-START-EDIT
           MOVE H-STATUS-END TO WS-END-EDIT
           MOVE SPACES TO WS-STATUS-LINE
           STRING "STATUS|order=" FUNCTION TRIM(H-ORDER)
           "|class=" FUNCTION TRIM(H-CLASS)
           "|priority=" WS-PRIORITY-EDIT
           "|revision=" WS-REVISION-EDIT
           "|state=" FUNCTION TRIM(H-STATE)
           "|booking=" FUNCTION TRIM(H-STATUS-BOOKING)
           "|bay=" FUNCTION TRIM(H-STATUS-BAY)
           "|technician=" FUNCTION TRIM(H-STATUS-TECH)
           "|start=" WS-START-EDIT
           "|end=" WS-END-EDIT
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
                WHERE work_order_id = :H-ORDER
                ORDER BY audit_sequence
           END-EXEC
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM work_order
         WHERE work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        PERFORM EMIT-DATABASE-ERROR
        MOVE 3 TO WS-EXIT-STATUS
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        DISPLAY "ERR|request=NONE|command=AUDIT|"
                "code=UNKNOWN_ORDER"
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
                   "|order=" FUNCTION TRIM(H-ORDER)
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
        WHEN "OPEN"
            PERFORM APPLY-OPEN
        WHEN "RESERVE"
            PERFORM APPLY-RESERVE
        WHEN "MOVE"
            PERFORM APPLY-MOVE
        WHEN "START"
            PERFORM APPLY-START
        WHEN "COMPLETE"
            PERFORM APPLY-COMPLETE
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
       
       APPLY-OPEN.
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM work_order
         WHERE work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT > 0
        PERFORM SET-ORDER-EXISTS
        EXIT PARAGRAPH
           END-IF
       
           EXEC SQL
        INSERT INTO work_order
            (work_order_id, equipment_class, priority,
             revision, state)
        VALUES
            (:H-ORDER, :H-CLASS, :H-PRIORITY, 1, 'OPEN')
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           MOVE 1 TO H-NEW-REVISION
           MOVE "NONE" TO WS-PRIOR-STATE
           MOVE "OPEN" TO WS-NEW-STATE
           MOVE "NONE" TO WS-BOOKING-OUT.
       
       APPLY-RESERVE.
           PERFORM LOAD-WORK-ORDER-FOR-UPDATE
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           IF H-EXPECTED-REVISION NOT = H-CURRENT-REVISION
        PERFORM SET-STALE-REVISION
        EXIT PARAGRAPH
           END-IF
           IF FUNCTION TRIM(H-STATE) NOT = "OPEN"
        PERFORM SET-INVALID-STATE
        EXIT PARAGRAPH
           END-IF
           PERFORM CHECK-RESOURCE-COMPATIBILITY
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           IF H-START-TICK >= H-END-TICK
        PERFORM SET-INVALID-WINDOW
        EXIT PARAGRAPH
           END-IF
           PERFORM CHECK-WINDOW-POLICY
           IF BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           PERFORM LOCK-REQUESTED-RESOURCES
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
           PERFORM CHECK-SCHEDULE-CONFLICT
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
       
           COMPUTE H-NEW-REVISION = H-CURRENT-REVISION + 1
           MOVE H-NEW-REVISION TO WS-REVISION-EDIT
           MOVE SPACES TO H-BOOKING
           STRING "BK-" FUNCTION TRIM(H-ORDER) "-" WS-REVISION-EDIT
             INTO H-BOOKING
           END-STRING
           EXEC SQL
        INSERT INTO booking
            (booking_id, work_order_id, bay_id, technician_id,
             start_tick, end_tick, policy_id, shift_code,
             supervision_level, capacity_percent, state, revision)
        VALUES
            (:H-BOOKING, :H-ORDER, :H-BAY, :H-TECHNICIAN,
             :H-START-TICK, :H-END-TICK, :H-POLICY-ID,
             :H-SHIFT-CODE, :H-SUPERVISION-LEVEL,
             :H-CAPACITY-PERCENT, 'RESERVED', 1)
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        UPDATE work_order
           SET state = 'RESERVED', revision = :H-NEW-REVISION
         WHERE work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           MOVE "OPEN" TO WS-PRIOR-STATE
           MOVE "RESERVED" TO WS-NEW-STATE
           MOVE H-BOOKING TO WS-BOOKING-OUT.
       
       APPLY-MOVE.
           EXEC SQL INCLUDE "move-transaction" END-EXEC.
       
       APPLY-START.
           PERFORM LOAD-WORK-ORDER-FOR-UPDATE
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           IF H-EXPECTED-REVISION NOT = H-CURRENT-REVISION
        PERFORM SET-STALE-REVISION
        EXIT PARAGRAPH
           END-IF
           IF FUNCTION TRIM(H-STATE) NOT = "RESERVED"
        PERFORM SET-INVALID-STATE
        EXIT PARAGRAPH
           END-IF
           PERFORM LOAD-ACTIVE-BOOKING
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
           COMPUTE H-NEW-REVISION = H-CURRENT-REVISION + 1
           EXEC SQL
        UPDATE booking
           SET state = 'STARTED', revision = revision + 1
         WHERE booking_id = :H-BOOKING
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        UPDATE work_order
           SET state = 'STARTED', revision = :H-NEW-REVISION
         WHERE work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           MOVE "RESERVED" TO WS-PRIOR-STATE
           MOVE "STARTED" TO WS-NEW-STATE
           MOVE H-BOOKING TO WS-BOOKING-OUT.
       
       APPLY-COMPLETE.
           PERFORM LOAD-WORK-ORDER-FOR-UPDATE
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           IF H-EXPECTED-REVISION NOT = H-CURRENT-REVISION
        PERFORM SET-STALE-REVISION
        EXIT PARAGRAPH
           END-IF
           IF FUNCTION TRIM(H-STATE) NOT = "STARTED"
        PERFORM SET-INVALID-STATE
        EXIT PARAGRAPH
           END-IF
           PERFORM LOAD-ACTIVE-BOOKING
           IF SQL-FAILED
        EXIT PARAGRAPH
           END-IF
           COMPUTE H-NEW-REVISION = H-CURRENT-REVISION + 1
           EXEC SQL
        UPDATE booking
           SET state = 'COMPLETED', revision = revision + 1
         WHERE booking_id = :H-BOOKING
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        UPDATE work_order
           SET state = 'COMPLETED', revision = :H-NEW-REVISION
         WHERE work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           MOVE "STARTED" TO WS-PRIOR-STATE
           MOVE "COMPLETED" TO WS-NEW-STATE
           MOVE H-BOOKING TO WS-BOOKING-OUT.
       
       APPLY-CANCEL.
           PERFORM LOAD-WORK-ORDER-FOR-UPDATE
           IF SQL-FAILED OR BUSINESS-FAILED
        EXIT PARAGRAPH
           END-IF
           IF H-EXPECTED-REVISION NOT = H-CURRENT-REVISION
        PERFORM SET-STALE-REVISION
        EXIT PARAGRAPH
           END-IF
           IF FUNCTION TRIM(H-STATE) NOT = "OPEN"
       AND FUNCTION TRIM(H-STATE) NOT = "RESERVED"
        PERFORM SET-INVALID-STATE
        EXIT PARAGRAPH
           END-IF
           MOVE H-STATE TO WS-PRIOR-STATE
           MOVE "NONE" TO H-BOOKING WS-BOOKING-OUT
           IF FUNCTION TRIM(H-STATE) = "RESERVED"
        PERFORM LOAD-ACTIVE-BOOKING
        IF SQL-FAILED
            EXIT PARAGRAPH
        END-IF
        EXEC SQL
            UPDATE booking
               SET state = 'CANCELLED', revision = revision + 1
             WHERE booking_id = :H-BOOKING
        END-EXEC
        IF SQLCODE NOT = 0
            SET SQL-FAILED TO TRUE
            EXIT PARAGRAPH
        END-IF
        MOVE H-BOOKING TO WS-BOOKING-OUT
           END-IF
           COMPUTE H-NEW-REVISION = H-CURRENT-REVISION + 1
           EXEC SQL
        UPDATE work_order
           SET state = 'CANCELLED', revision = :H-NEW-REVISION
         WHERE work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           MOVE "CANCELLED" TO WS-NEW-STATE.
       
       LOAD-WORK-ORDER-FOR-UPDATE.
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM work_order
         WHERE work_order_id = :H-ORDER
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        PERFORM SET-UNKNOWN-ORDER
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        SELECT equipment_class, priority, revision, state
          INTO :H-CLASS, :H-PRIORITY, :H-CURRENT-REVISION,
               :H-STATE
          FROM work_order
         WHERE work_order_id = :H-ORDER
           FOR UPDATE
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
           END-IF.
       
       LOAD-ACTIVE-BOOKING.
           MOVE SPACES TO H-BOOKING
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM booking
         WHERE work_order_id = :H-ORDER
           AND state IN ('RESERVED', 'STARTED')
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 1
        EXEC SQL
            SELECT booking_id, revision
              INTO :H-BOOKING, :H-BOOKING-REVISION
              FROM booking
             WHERE work_order_id = :H-ORDER
               AND state IN ('RESERVED', 'STARTED')
               FOR UPDATE
        END-EXEC
        IF SQLCODE NOT = 0
            SET SQL-FAILED TO TRUE
        END-IF
           ELSE
        SET SQL-FAILED TO TRUE
           END-IF.
       
       CHECK-RESOURCE-COMPATIBILITY.
           MOVE 0 TO H-COUNT H-BAY-ACTIVE H-TECH-ACTIVE
           MOVE SPACES TO H-BAY-CAPABILITY H-TECH-CERTIFICATION
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM workshop_bay
         WHERE bay_id = :H-BAY
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        PERFORM SET-UNKNOWN-RESOURCE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        SELECT capability, CASE WHEN active THEN 1 ELSE 0 END
          INTO :H-BAY-CAPABILITY, :H-BAY-ACTIVE
          FROM workshop_bay
         WHERE bay_id = :H-BAY
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
       
           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM technician
         WHERE technician_id = :H-TECHNICIAN
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           IF H-COUNT = 0
        PERFORM SET-UNKNOWN-RESOURCE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        SELECT certification, CASE WHEN active THEN 1 ELSE 0 END
          INTO :H-TECH-CERTIFICATION, :H-TECH-ACTIVE
          FROM technician
         WHERE technician_id = :H-TECHNICIAN
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
       
           IF H-BAY-ACTIVE NOT = 1 OR H-TECH-ACTIVE NOT = 1
        PERFORM SET-UNKNOWN-RESOURCE
        EXIT PARAGRAPH
           END-IF
           IF (FUNCTION TRIM(H-BAY-CAPABILITY)
        NOT = FUNCTION TRIM(H-CLASS)
        AND FUNCTION TRIM(H-BAY-CAPABILITY) NOT = "UNIVERSAL")
       OR (FUNCTION TRIM(H-TECH-CERTIFICATION)
           NOT = FUNCTION TRIM(H-CLASS)
        AND FUNCTION TRIM(H-TECH-CERTIFICATION)
            NOT = "UNIVERSAL")
        PERFORM SET-INCOMPATIBLE-RESOURCE
           END-IF.

       CHECK-WINDOW-POLICY.
           MOVE "N" TO WS-POLICY-ALLOWED
           MOVE 0 TO WS-POLICY-MAX-DURATION
           MOVE SPACES TO H-POLICY-ID H-SHIFT-CODE
           MOVE 0 TO H-SUPERVISION-LEVEL H-CAPACITY-PERCENT
           CALL "WORKSHOP-POLICY-ENGINE" USING
                H-CLASS
                H-PRIORITY
                H-START-TICK
                H-END-TICK
                WS-POLICY-ALLOWED
                WS-POLICY-MAX-DURATION
                H-POLICY-ID
                H-SHIFT-CODE
                H-SUPERVISION-LEVEL
                H-CAPACITY-PERCENT
           END-CALL
           IF WS-POLICY-ALLOWED NOT = "Y"
        PERFORM SET-INVALID-WINDOW
           END-IF.
       
       LOCK-REQUESTED-RESOURCES.
           EXEC SQL INCLUDE "resource-lock" END-EXEC.
       
       CHECK-SCHEDULE-CONFLICT.
           EXEC SQL INCLUDE "overlap-check" END-EXEC.
       
       RECORD-BUSINESS-REJECTION.
           PERFORM BUILD-ERROR-RESPONSE
           EXEC SQL
        INSERT INTO request_record
            (request_id, command_name, fingerprint,
             response_line,
             work_order_id)
        VALUES
            (:H-REQUEST, :H-COMMAND, :H-FINGERPRINT, :H-RESPONSE,
             :H-ORDER)
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
             response_line,
             work_order_id)
        VALUES
            (:H-REQUEST, :H-COMMAND, :H-FINGERPRINT, :H-RESPONSE,
             :H-ORDER)
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF
           EXEC SQL
        INSERT INTO audit_event
            (audit_sequence, request_id, work_order_id, action,
             prior_state, new_state, resulting_revision)
        VALUES
            (:H-AUDIT-SEQUENCE, :H-REQUEST, :H-ORDER, :H-COMMAND,
             :WS-PRIOR-STATE, :WS-NEW-STATE, :H-NEW-REVISION)
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
           END-IF.
       
       BUILD-SUCCESS-RESPONSE.
           MOVE H-NEW-REVISION TO WS-REVISION-EDIT
           MOVE H-AUDIT-SEQUENCE TO WS-AUDIT-EDIT
           MOVE SPACES TO WS-RESPONSE-WORK H-RESPONSE
           STRING "OK|request=" FUNCTION TRIM(H-REQUEST)
           "|command=" FUNCTION TRIM(H-COMMAND)
           "|order=" FUNCTION TRIM(H-ORDER)
           "|booking=" FUNCTION TRIM(WS-BOOKING-OUT)
           "|revision=" WS-REVISION-EDIT
           "|state=" FUNCTION TRIM(WS-NEW-STATE)
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
       
       SET-ORDER-EXISTS.
           SET BUSINESS-FAILED TO TRUE
           MOVE "ORDER_EXISTS" TO WS-BUSINESS-CODE.
       
       SET-UNKNOWN-ORDER.
           SET BUSINESS-FAILED TO TRUE
           MOVE "UNKNOWN_ORDER" TO WS-BUSINESS-CODE.
       
       SET-STALE-REVISION.
           SET BUSINESS-FAILED TO TRUE
           MOVE "STALE_REVISION" TO WS-BUSINESS-CODE.
       
       SET-INVALID-STATE.
           SET BUSINESS-FAILED TO TRUE
           MOVE "INVALID_STATE" TO WS-BUSINESS-CODE.
       
       SET-UNKNOWN-RESOURCE.
           SET BUSINESS-FAILED TO TRUE
           MOVE "UNKNOWN_RESOURCE" TO WS-BUSINESS-CODE.
       
       SET-INCOMPATIBLE-RESOURCE.
           SET BUSINESS-FAILED TO TRUE
           MOVE "INCOMPATIBLE_RESOURCE" TO WS-BUSINESS-CODE.
       
       SET-INVALID-WINDOW.
           SET BUSINESS-FAILED TO TRUE
           MOVE "INVALID_WINDOW" TO WS-BUSINESS-CODE.
       
       SET-RESOURCE-BUSY.
           SET BUSINESS-FAILED TO TRUE
           MOVE "RESOURCE_BUSY" TO WS-BUSINESS-CODE.
       
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
       
       END PROGRAM WORKSHOP-TERMINAL.
