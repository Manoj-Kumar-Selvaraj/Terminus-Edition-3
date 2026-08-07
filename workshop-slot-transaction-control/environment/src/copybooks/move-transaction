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
       EXEC SQL
           UPDATE booking
              SET bay_id = :H-BAY,
                  technician_id = :H-TECHNICIAN,
                  start_tick = :H-START-TICK,
                  end_tick = :H-END-TICK,
                  revision = revision + 1
            WHERE booking_id = :H-BOOKING
       END-EXEC
       IF SQLCODE NOT = 0
           SET SQL-FAILED TO TRUE
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
       EXEC SQL
           UPDATE booking
              SET policy_id = :H-POLICY-ID,
                  shift_code = :H-SHIFT-CODE,
                  supervision_level = :H-SUPERVISION-LEVEL,
                  capacity_percent = :H-CAPACITY-PERCENT
            WHERE booking_id = :H-BOOKING
       END-EXEC
       IF SQLCODE NOT = 0
           SET SQL-FAILED TO TRUE
           EXIT PARAGRAPH
       END-IF
       EXEC SQL
           UPDATE work_order
              SET revision = :H-NEW-REVISION
            WHERE work_order_id = :H-ORDER
       END-EXEC
       IF SQLCODE NOT = 0
           SET SQL-FAILED TO TRUE
           EXIT PARAGRAPH
       END-IF
       MOVE "RESERVED" TO WS-PRIOR-STATE WS-NEW-STATE
       MOVE H-BOOKING TO WS-BOOKING-OUT.
