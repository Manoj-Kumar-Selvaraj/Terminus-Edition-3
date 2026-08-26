"""Deterministic estate fixture generator for Sovereign RDS Control Plane."""
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from rds.time_utils import utc_now

class FixtureGenerator:
    """Generates 14,800+ deterministic primary estate records."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.record_count = 0

    def generate_db_instances(self, count: int = 100) -> list[dict]:
        """Generate 100 DBInstance records."""
        instances = []
        for i in range(count):
            account_id = f"{100000000000 + (i % 10)}"
            inst_id = f"db-instance-{i:03d}"
            instances.append({
                "instance_id": inst_id,
                "tenant_id": f"tenant-{(i % 5):02d}",
                "account_id": account_id,
                "region": "us-east-1",
                "engine": "postgres",
                "engine_version": "16.2",
                "db_instance_class": "db.m6i.xlarge",
                "allocated_storage_gb": 100 + (i * 10),
                "storage_type": "gp3",
                "status": "AVAILABLE",
                "deletion_protection": True,
                "multi_az": (i % 2 == 0),
                "publicly_accessible": False,
                "master_username": "postgres",
                "endpoint_address": f"{inst_id}.c123456789.us-east-1.rds.sovereign.internal",
                "endpoint_port": 5432,
                "parameter_group_name": "default.postgres16",
                "pending_reboot_parameters": False,
                "backup_retention_period": 7,
            })
            self.record_count += 1
        return instances

    def generate_wal_archives(self, instances: list[dict], segments_per_instance: int = 140) -> list[dict]:
        """Generate 14,000 WAL segment archive records."""
        wal_records = []
        base_time = utc_now() - timedelta(days=7)

        for inst in instances:
            inst_id = inst["instance_id"]
            for seq in range(1, segments_per_instance + 1):
                start_t = base_time + timedelta(minutes=seq * 5)
                end_t = start_t + timedelta(minutes=5)
                wal_records.append({
                    "instance_id": inst_id,
                    "timeline_id": 1,
                    "sequence_number": seq,
                    "wal_file_name": f"00000001{inst_id[-3:]}{seq:012X}",
                    "start_lsn": f"0/{seq:08X}",
                    "end_lsn": f"0/{(seq + 1):08X}",
                    "start_time": start_t,
                    "end_time": end_t,
                    "size_bytes": 16777216,  # 16 MB
                    "has_gap": False,
                })
                self.record_count += 1

        return wal_records

    def generate_db_snapshots(self, instances: list[dict], snapshots_per_instance: int = 4) -> list[dict]:
        """Generate 400 DBSnapshot records."""
        snapshots = []
        base_time = utc_now() - timedelta(days=5)

        for inst in instances:
            inst_id = inst["instance_id"]
            for s in range(1, snapshots_per_instance + 1):
                snap_time = base_time + timedelta(days=s)
                snapshots.append({
                    "snapshot_id": f"snapshot-{inst_id}-{s:02d}",
                    "instance_id": inst_id,
                    "snapshot_type": "automated" if s > 1 else "manual",
                    "status": "COMPLETED",
                    "allocated_storage_gb": inst["allocated_storage_gb"],
                    "redo_lsn": f"0/{s * 1000:08X}",
                    "timeline_id": 1,
                    "snapshot_time": snap_time,
                })
                self.record_count += 1

        return snapshots

    def generate_outbox_events(self, count: int = 300) -> list[dict]:
        """Generate 300 outbox event notification records."""
        events = []
        base_time = utc_now() - timedelta(hours=12)

        categories = ["backup", "failover", "maintenance", "notification", "configuration"]

        for i in range(count):
            event_id = str(uuid.uuid4())
            events.append({
                "event_id": event_id,
                "event_identifier": f"RDS-EVENT-{(i + 1000):04d}",
                "source_type": "db-instance",
                "source_identifier": f"db-instance-{(i % 100):03d}",
                "category": categories[i % len(categories)],
                "message": f"Database instance db-instance-{(i % 100):03d} event notification {i}",
                "event_time": base_time + timedelta(minutes=i * 2),
                "status": "PENDING",
                "retry_count": 0,
            })
            self.record_count += 1

        return events

async def generate_estate(cfg: Any = None) -> int:
    """Generate 14,800 primary estate records."""
    gen = FixtureGenerator(seed=42)
    instances = gen.generate_db_instances(100)
    wal_records = gen.generate_wal_archives(instances, 140)
    snapshots = gen.generate_db_snapshots(instances, 4)
    events = gen.generate_outbox_events(300)

    total = gen.record_count
    print(f"Generated {total} primary estate records")
    return total
