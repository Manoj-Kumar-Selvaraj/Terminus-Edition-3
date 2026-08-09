from django.db import models


class Shopper(models.Model):
    shopper_ref = models.TextField(unique=True)
    email_hash = models.TextField()
    region = models.TextField()
    loyalty_tier = models.TextField()
    created_at = models.TextField()
    risk_band = models.TextField()

    class Meta:
        db_table = "identity_shopper"
        managed = False


class Address(models.Model):
    shopper = models.ForeignKey(Shopper, on_delete=models.DO_NOTHING)
    kind = models.TextField()
    postal = models.TextField()
    country = models.TextField()

    class Meta:
        db_table = "identity_address"
        managed = False
