from django.db import models


class SideEffect(models.Model):
    attempt_id = models.TextField()
    kind = models.TextField()
    payload_hash = models.TextField()
    status = models.TextField()
    delivered_at = models.TextField(null=True)
    write_lsn = models.IntegerField()

    class Meta:
        db_table = "fulfill_side_effect"
        managed = False


class WebhookDelivery(models.Model):
    side_effect = models.ForeignKey(SideEffect, on_delete=models.DO_NOTHING)
    target = models.TextField()
    attempt_no = models.IntegerField()
    http_status = models.IntegerField()

    class Meta:
        db_table = "fulfill_webhook"
        managed = False
