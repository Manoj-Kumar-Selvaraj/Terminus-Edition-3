WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<15000)
INSERT INTO historical_movements(event_id,cycle_day,warehouse_id,item_id,movement_type,status,quantity_variant,value_variant)
SELECT x,1+(x%180),printf('W%02d',1+(x%8)),printf('SKU%05d',1+(x%1000)),CASE x%4 WHEN 0 THEN 'RECEIPT' WHEN 1 THEN 'ISSUE' WHEN 2 THEN 'TRANSFER' ELSE 'ADJUSTMENT' END,CASE x%3 WHEN 0 THEN 'ACCEPTED' WHEN 1 THEN 'REJECTED' ELSE 'HELD' END,x,15001-x FROM n;
