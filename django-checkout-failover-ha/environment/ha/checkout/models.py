from django.db import models

from catalog.models import Product, Warehouse
from identity.models import Shopper


class Cart(models.Model):
    shopper = models.ForeignKey(Shopper, on_delete=models.DO_NOTHING)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.DO_NOTHING)
    status = models.TextField()
    currency = models.TextField()
    updated_at = models.TextField()

    class Meta:
        db_table = "checkout_cart"
        managed = False


class CartLine(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.DO_NOTHING)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING)
    qty = models.IntegerField()

    class Meta:
        db_table = "checkout_cartline"
        managed = False


class CheckoutAttempt(models.Model):
    attempt_id = models.TextField(unique=True)
    cart = models.ForeignKey(Cart, on_delete=models.DO_NOTHING)
    shopper = models.ForeignKey(Shopper, on_delete=models.DO_NOTHING)
    idempotency_key = models.TextField()
    status = models.TextField()
    az_origin = models.TextField()
    created_at = models.TextField()

    class Meta:
        db_table = "checkout_attempt"
        managed = False


class Order(models.Model):
    order_ref = models.TextField(unique=True)
    shopper = models.ForeignKey(Shopper, on_delete=models.DO_NOTHING)
    attempt_id = models.TextField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.DO_NOTHING)
    status = models.TextField()
    channel = models.TextField()
    currency = models.TextField()
    total_cents = models.IntegerField()
    az_origin = models.TextField()
    placed_at = models.TextField()
    write_lsn = models.IntegerField()

    class Meta:
        db_table = "checkout_order"
        managed = False


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.DO_NOTHING)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING)
    qty = models.IntegerField()
    unit_cents = models.IntegerField()

    class Meta:
        db_table = "checkout_orderline"
        managed = False


class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.DO_NOTHING)
    provider_ref = models.TextField()
    status = models.TextField()
    amount_cents = models.IntegerField()
    captured_at = models.TextField(null=True)

    class Meta:
        db_table = "checkout_payment"
        managed = False
