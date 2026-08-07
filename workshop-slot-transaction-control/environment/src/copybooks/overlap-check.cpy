           MOVE 0 TO H-COUNT
           EXEC SQL
        SELECT COUNT(*) INTO :H-COUNT
          FROM booking
         WHERE state IN ('RESERVED', 'STARTED')
           AND work_order_id <> :H-ORDER
           AND start_tick <= :H-END-TICK
           AND end_tick >= :H-START-TICK
           AND bay_id = :H-BAY
           END-EXEC
           IF SQLCODE NOT = 0
        SET SQL-FAILED TO TRUE
        EXIT PARAGRAPH
           END-IF.
           IF H-COUNT > 0
        PERFORM SET-RESOURCE-BUSY
           END-IF.
