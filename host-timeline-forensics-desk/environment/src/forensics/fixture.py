"""Deterministic synthetic estate bootstrap for the local forensic lab."""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from psycopg.types.json import Jsonb

from .canonical import digest_json, sha256_bytes
from .config import get_settings
from .database import Database

SEED_VERSION = "synthetic-forensic-estate-v1"
PRIMARY_RECORD_COUNT = 14_200
TENANTS = 20
ACTORS = 160
CASES = 240
ENDPOINTS = 600
POLICIES = 200
PLANS = 240
ITEMS = 2_000
ATTEMPTS = 3_000
OBJECTS = 2_500
EVIDENCE = 2_500
CUSTODY = 2_000
OBSERVATIONS = 500
HOLDS = 200
EXPORTS = 280
RECORD_FAMILIES = (
    ("tenant", TENANTS), ("actor", ACTORS), ("case", CASES),
    ("endpoint", ENDPOINTS), ("policy", POLICIES), ("collection_item", ITEMS),
    ("collection_attempt", ATTEMPTS), ("evidence_object", OBJECTS),
    ("evidence_item", EVIDENCE), ("custody_event", CUSTODY),
    ("event_observation", OBSERVATIONS), ("case_hold", HOLDS),
    ("export_job", EXPORTS),
)
assert sum(count for _, count in RECORD_FAMILIES) == PRIMARY_RECORD_COUNT
PLATFORMS = ("linux", "windows", "macos")
SITES = ("north", "south", "west", "lab")
SOURCES = ("filesystem", "eventlog", "volatile-state", "registry", "browser", "execution-trace")
ARTIFACTS = ("filesystem.metadata", "eventlog.system", "volatile.processes", "registry.autoruns", "browser.history", "execution.prefetch")
BASE_TIME = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)


def _id(prefix: str, number: int, width: int = 6) -> str:
    return f"{prefix}-{number:0{width}d}"


def _tenant_for(index: int) -> str:
    return _id("tenant", index % TENANTS + 1, 2)


def _case_for(index: int) -> str:
    return _id("CASE", index % CASES + 1, 6)


def _endpoint_for(index: int) -> str:
    return _id("HOST", index % ENDPOINTS + 1, 6)


def _deterministic_blob(identity: str) -> bytes:
    seed = hashlib.sha256((SEED_VERSION + ":" + identity).encode()).digest()
    return b"SYNTHETIC-EVIDENCE\x00" + seed + seed[:13]


def seed_records(database: Database, *, evidence_root: Path | None = None) -> dict[str, int]:
    """Create a stable, varied primary estate and its queryable domain projections."""
    root = evidence_root or get_settings().evidence_root
    root.mkdir(parents=True, exist_ok=True)
    with database.transaction("SERIALIZABLE") as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("forensics-seed-v1",))
        found = conn.execute("SELECT count(*) AS n FROM seed_records").fetchone()
        if int(found["n"] or 0) == PRIMARY_RECORD_COUNT:
            return {"primary_records": PRIMARY_RECORD_COUNT, "seed_version": SEED_VERSION}
        if int(found["n"] or 0):
            raise RuntimeError("partial synthetic seed exists; reset the disposable database")

        tenants = [(_tenant_for(i), f"Synthetic response tenant {i:02d}") for i in range(TENANTS)]
        conn.cursor().executemany(
            "INSERT INTO tenants(tenant_id,display_name) VALUES(%s,%s) ON CONFLICT DO NOTHING", tenants
        )
        actor_rows: list[tuple] = []
        membership_rows: list[tuple] = []
        for i in range(ACTORS):
            tenant = _tenant_for(i // 8)
            actor = _id("analyst", i + 1)
            role = "tenant_admin" if i % 8 == 0 else ("custodian" if i % 8 == 1 else "analyst")
            actor_rows.append((actor, tenant, role))
        conn.cursor().executemany(
            "INSERT INTO actors(actor_id,tenant_id,role) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING", actor_rows
        )

        case_rows: list[tuple] = []
        for i in range(CASES):
            tenant = _tenant_for(i // 12)
            case = _id("CASE", i + 1)
            state = "hold" if i % 29 == 0 else ("closed" if i % 11 == 0 else "open")
            case_rows.append((case, tenant, f"Synthetic response {i + 1:04d}", state, 1 + i % 5, BASE_TIME, BASE_TIME))
        conn.cursor().executemany(
            "INSERT INTO cases(case_id,tenant_id,title,state,revision,opened_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            case_rows,
        )
        for i in range(CASES):
            case = _id("CASE", i + 1)
            tenant_idx = i // 12
            for offset, permission in enumerate(("case:inspect", "case:collect", "case:export", "case:hold")):
                actor = _id("analyst", tenant_idx * 8 + offset + 1)
                membership_rows.append((case, actor, permission, BASE_TIME))
        conn.cursor().executemany(
            "INSERT INTO case_memberships(case_id,actor_id,permission,granted_at) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            membership_rows,
        )

        endpoint_rows: list[tuple] = []
        for i in range(ENDPOINTS):
            tenant = _tenant_for(i // 30)
            platform = PLATFORMS[i % len(PLATFORMS)]
            capabilities = {"sources": list(SOURCES[:2 + i % len(SOURCES)]), "max_bytes": 50_000_000 + (i % 9) * 10_000_000}
            endpoint_rows.append((_id("HOST", i + 1), tenant, platform, SITES[i % len(SITES)], "active", 1 + i % 4, Jsonb(capabilities), BASE_TIME - timedelta(minutes=i % 7000)))
        conn.cursor().executemany(
            "INSERT INTO endpoints(endpoint_id,tenant_id,platform,site_id,state,inventory_generation,capabilities,last_seen_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            endpoint_rows,
        )

        policy_rows: list[tuple] = []
        for i in range(POLICIES):
            tenant = _tenant_for(i // 10)
            revision = f"POL-{i + 1:04d}"
            policy = {"allowed_modes": ["live", "offline"] if i % 3 else ["offline"], "allowed_sources": list(SOURCES[:3 + i % 4]), "max_case_bytes": 200_000_000 + (i % 7) * 25_000_000, "require_complete_digest": True}
            policy_rows.append((tenant, revision, Jsonb(policy), digest_json(policy), BASE_TIME - timedelta(days=i % 365)))
        conn.cursor().executemany(
            "INSERT INTO policy_revisions(tenant_id,policy_revision,document,digest,created_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            policy_rows,
        )

        plan_rows: list[tuple] = []
        for i in range(PLANS):
            case_idx = i % CASES
            case = _id("CASE", case_idx + 1)
            tenant = _tenant_for(case_idx // 12)
            policy_index = (case_idx // 12) * 10 + i % 10
            policy_revision = f"POL-{policy_index + 1:04d}"
            actor = _id("analyst", (case_idx // 12) * 8 + 1)
            plan_id = _id("plan", i + 1)
            intent = {"case_id": case, "tenant_id": tenant, "policy_revision": policy_revision, "synthetic": True}
            plan_rows.append((plan_id, tenant, case, 1, policy_revision, 1 + i % 4, actor, Jsonb(intent), digest_json(intent), "complete", BASE_TIME - timedelta(days=i % 80)))
        conn.cursor().executemany(
            "INSERT INTO collection_plans(plan_id,tenant_id,case_id,case_revision,policy_revision,inventory_generation,requested_by,intent,plan_digest,state,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            plan_rows,
        )
        conn.cursor().executemany(
            "INSERT INTO plan_revisions(plan_id,revision,digest,document,created_at) VALUES(%s,1,%s,%s,%s) ON CONFLICT DO NOTHING",
            [(row[0], row[8], row[7], row[10]) for row in plan_rows],
        )

        item_rows: list[tuple] = []
        disposition_rows: list[tuple] = []
        for i in range(ITEMS):
            case_idx = i % CASES
            plan_id = _id("plan", case_idx + 1)
            case = _id("CASE", case_idx + 1)
            tenant = _tenant_for(case_idx // 12)
            endpoint_local = (i * 7) % 30
            endpoint_idx = (case_idx // 12) * 30 + endpoint_local
            endpoint = _id("HOST", endpoint_idx + 1)
            source = SOURCES[i % len(SOURCES)]
            mode = "offline" if i % 4 == 0 else "live"
            item_id = _id("item", i + 1)
            families = [ARTIFACTS[i % len(ARTIFACTS)]]
            deadline = BASE_TIME + timedelta(hours=(i % 96) + 1)
            disposition = ("complete", "partial", "unavailable", "rejected", "complete")[i % 5]
            item_rows.append((item_id, plan_id, case, endpoint, source, mode, Jsonb(families), 5_000_000 + i % 500_000, deadline, i % 7 != 0, disposition, 1 + i % 2, BASE_TIME, BASE_TIME))
            disposition_rows.append((item_id, tenant, case, endpoint, source, disposition, 1024 + i % 50_000, None, None, BASE_TIME))
        conn.cursor().executemany(
            "INSERT INTO collection_items(item_id,plan_id,case_id,endpoint_id,source_id,mode,artifact_families,byte_limit,deadline,required,disposition,active_attempt,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            item_rows,
        )
        conn.cursor().executemany(
            "INSERT INTO source_dispositions(item_id,tenant_id,case_id,endpoint_id,source_id,disposition,accepted_bytes,expected_bytes,terminal_reason,last_observation_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            disposition_rows,
        )

        attempt_rows: list[tuple] = []
        for i in range(ATTEMPTS):
            item = _id("item", i % ITEMS + 1)
            attempt = i // ITEMS + 1
            worker = _id("worker", i % 24 + 1)
            token = hashlib.sha256(f"{SEED_VERSION}:attempt:{i}".encode()).hexdigest()
            state = "complete" if i % 4 else "partial"
            attempt_rows.append((item, attempt, worker, token, state, BASE_TIME, BASE_TIME, BASE_TIME, hashlib.sha256(token.encode()).hexdigest(), Jsonb({"synthetic": True, "sequence": i}), BASE_TIME, BASE_TIME))
        conn.cursor().executemany(
            "INSERT INTO collection_attempts(item_id,attempt,worker_id,attempt_token,state,dispatched_at,acknowledged_at,completed_at,result_digest,result_payload,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            attempt_rows,
        )

        object_rows: list[tuple] = []
        evidence_rows: list[tuple] = []
        object_files: list[tuple[Path, bytes]] = []
        for i in range(OBJECTS):
            evidence_id = _id("evidence", i + 1)
            payload = b"SYNTHETIC\x00" + hashlib.sha256(f"{SEED_VERSION}:{evidence_id}".encode()).digest()
            digest = sha256_bytes(payload)
            relative = Path(digest[:2]) / (digest + ".bin")
            object_files.append((root / relative, payload))
            object_rows.append((digest, len(payload), str(relative), True, BASE_TIME))
            item_idx = i % ITEMS
            case_idx = item_idx % CASES
            tenant = _tenant_for(case_idx // 12)
            item_id = _id("item", item_idx + 1)
            endpoint = _id("HOST", ((case_idx // 12) * 30 + (item_idx * 7) % 30) + 1)
            evidence_rows.append((evidence_id, tenant, _id("CASE", case_idx + 1), endpoint, SOURCES[i % len(SOURCES)], _id("plan", case_idx + 1), item_id, 1 + item_idx % 2, digest, BASE_TIME - timedelta(minutes=i % 9000), Jsonb(["synthetic"] if i % 9 == 0 else []), "verified", BASE_TIME))
        for path, payload in object_files:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(payload)
        conn.cursor().executemany(
            "INSERT INTO evidence_objects(digest,byte_length,object_path,complete,created_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            object_rows,
        )
        conn.cursor().executemany(
            "INSERT INTO evidence_items(evidence_id,tenant_id,case_id,endpoint_id,source_id,plan_id,item_id,attempt,digest,capture_time,traits,validation_state,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            evidence_rows,
        )

        custody_rows: list[tuple] = []
        for i in range(CUSTODY):
            evidence_id = _id("evidence", i % EVIDENCE + 1)
            item = evidence_rows[i % EVIDENCE]
            tenant, case = item[1], item[2]
            custody_id = _id("custody", i + 1)
            actor = _id("analyst", (i % ACTORS) + 1)
            action = ("acquired", "validated", "reviewed", "transferred")[i % 4]
            detail = {"action": action, "evidence_id": evidence_id, "actor": actor, "sequence": i}
            custody_rows.append((custody_id, tenant, case, evidence_id, actor, action, "synthetic seed history", digest_json(detail), BASE_TIME - timedelta(hours=i % 8000)))
        conn.cursor().executemany(
            "INSERT INTO custody_events(custody_id,tenant_id,case_id,evidence_id,actor_id,action,reason,event_digest,occurred_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            custody_rows,
        )

        hold_rows = []
        for i in range(HOLDS):
            case_idx = i % CASES
            tenant = _tenant_for(case_idx // 12)
            hold_rows.append((_id("hold", i + 1), tenant, _id("CASE", case_idx + 1), f"synthetic preservation hold {i + 1}", "active" if i % 3 else "released", _id("analyst", (case_idx // 12) * 8 + 2), BASE_TIME - timedelta(days=i % 60), None, None))
        conn.cursor().executemany(
            "INSERT INTO case_holds(hold_id,tenant_id,case_id,reason,state,created_by,created_at,released_by,released_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            hold_rows,
        )

        export_rows = []
        for i in range(EXPORTS):
            case_idx = i % CASES
            tenant = _tenant_for(case_idx // 12)
            export_rows.append((_id("export", i + 1), tenant, _id("CASE", case_idx + 1), _id("analyst", (case_idx // 12) * 8 + 3), "published" if i % 4 else "failed", hashlib.sha256(f"export:{i}".encode()).hexdigest(), f"seed/{_id('export',i+1)}.json", 1 + i % 42, BASE_TIME - timedelta(days=i % 30), BASE_TIME - timedelta(days=i % 30)))
        conn.cursor().executemany(
            "INSERT INTO export_jobs(export_id,tenant_id,case_id,requested_by,state,manifest_digest,object_path,item_count,created_at,published_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            export_rows,
        )

        # SQLite is used only as a deterministic seed-script interpreter; PostgreSQL
        # remains the runtime source of truth after these metadata rows are loaded.
        data_dir = Path(__file__).resolve().parents[1] / "data"
        seed_db = sqlite3.connect(":memory:")
        try:
            seed_db.executescript((data_dir / "seed_schema.sql").read_text(encoding="utf-8"))
            seed_db.executescript((data_dir / "seed.sql").read_text(encoding="utf-8"))
            seed_data = seed_db.execute(
                "SELECT record_id,record_type,tenant_id,case_id,endpoint_id,platform,site_id,source_id,acquisition_mode,disposition,artifact_family FROM seed_records ORDER BY record_id"
            ).fetchall()
        finally:
            seed_db.close()
        if len(seed_data) != PRIMARY_RECORD_COUNT:
            raise RuntimeError(f"canonical seed contains {len(seed_data)} rows; expected {PRIMARY_RECORD_COUNT}")
        seed_rows: list[tuple] = []
        for record_id, family, tenant, case_id, endpoint_id, platform, site, source, mode, disposition, artifact_family in seed_data:
            payload = {
                "record_type": family,
                "endpoint_id": endpoint_id,
                "platform": platform,
                "site_id": site,
                "source": source,
                "mode": mode,
                "disposition": disposition,
                "artifact_family": artifact_family,
                "seed": SEED_VERSION,
                "synthetic": True,
            }
            seed_rows.append((record_id, family, tenant, case_id, Jsonb(payload)))
        conn.cursor().executemany(
            "INSERT INTO seed_records(record_id,record_type,tenant_id,case_id,payload) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            seed_rows,
        )
    return {"primary_records": PRIMARY_RECORD_COUNT, "seed_version": SEED_VERSION, "families": dict(RECORD_FAMILIES)}
