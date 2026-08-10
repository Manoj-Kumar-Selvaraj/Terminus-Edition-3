from django.db import models


class Watermark(models.Model):
    role = models.TextField(primary_key=True)
    wal_lsn = models.IntegerField()
    applied_lsn = models.IntegerField()
    updated_at = models.TextField()

    class Meta:
        db_table = "ha_watermark"
        managed = False


class FenceLease(models.Model):
    resource = models.TextField(primary_key=True)
    owner_node = models.TextField()
    epoch = models.IntegerField()
    writable = models.IntegerField()
    fenced_until = models.TextField()

    class Meta:
        db_table = "ha_fence_lease"
        managed = False


class Node(models.Model):
    node_id = models.TextField(primary_key=True)
    role = models.TextField()
    last_seen = models.TextField()
    ready = models.IntegerField()

    class Meta:
        db_table = "ha_node"
        managed = False


class ShopSession(models.Model):
    session_key = models.TextField(primary_key=True)
    session_data = models.TextField()
    expire_date = models.TextField()

    class Meta:
        db_table = "django_session"
        managed = False
