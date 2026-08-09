from django.db import models

from catalog.models import Product, Warehouse


class StockLot(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.DO_NOTHING)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING)
    lot_code = models.TextField()
    qty_on_hand = models.IntegerField()
    qty_reserved = models.IntegerField()

    class Meta:
        db_table = "inventory_stocklot"
        managed = False


class Reservation(models.Model):
    stocklot = models.ForeignKey(StockLot, on_delete=models.DO_NOTHING)
    attempt_id = models.TextField()
    qty = models.IntegerField()
    status = models.TextField()
    created_at = models.TextField()

    class Meta:
        db_table = "inventory_reservation"
        managed = False
