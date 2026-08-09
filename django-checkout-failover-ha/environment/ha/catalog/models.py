from django.db import models


class Warehouse(models.Model):
    code = models.TextField(unique=True)
    region = models.TextField()
    az_id = models.TextField()
    status = models.TextField()
    city = models.TextField()

    class Meta:
        db_table = "catalog_warehouse"
        managed = False


class Product(models.Model):
    sku = models.TextField(unique=True)
    name = models.TextField()
    category = models.TextField()
    active = models.IntegerField()
    fulfillment_class = models.TextField()

    class Meta:
        db_table = "catalog_product"
        managed = False


class PriceBook(models.Model):
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING)
    currency = models.TextField()
    unit_cents = models.IntegerField()
    effective_from = models.TextField()

    class Meta:
        db_table = "catalog_pricebook"
        managed = False
