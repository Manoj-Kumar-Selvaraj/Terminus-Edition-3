"""Endpoint capability inventory and generation-scoped lookups."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from psycopg.types.json import Jsonb
from .canonical import normalize_endpoint_id
from .database import Database
from .errors import Conflict, InvalidRequest, NotFound


class InventoryService:
    def __init__(self, database: Database):
        self.db = database

    def generation(self, tenant_id: str) -> int:
        row = self.db.one(
            "SELECT coalesce(max(inventory_generation),0) AS generation "
            "FROM endpoints WHERE tenant_id=%s",
            (tenant_id,),
        )
        return int((row or {}).get("generation") or 0)

    def get_endpoint(self, tenant_id: str, endpoint_id: str) -> dict[str, Any]:
        normalized = normalize_endpoint_id(endpoint_id)
        row = self.db.one(
            "SELECT endpoint_id,tenant_id,platform,site_id,state,inventory_generation,capabilities,last_seen_at "
            "FROM endpoints WHERE tenant_id=%s AND endpoint_id=%s",
            (tenant_id, normalized),
        )
        if row is None:
            raise NotFound("endpoint is not present in tenant inventory")
        return row

    def list_endpoints(self, tenant_id: str, *, site_id: str | None = None,
                       platform: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        conditions = ["tenant_id=%s"]
        values: list[Any] = [tenant_id]
        if site_id:
            conditions.append("site_id=%s")
            values.append(site_id)
        if platform:
            conditions.append("platform=%s")
            values.append(platform)
        values.append(max(1, min(limit, 1000)))
        return self.db.query(
            "SELECT endpoint_id,platform,site_id,state,inventory_generation,capabilities,last_seen_at "
            f"FROM endpoints WHERE {' AND '.join(conditions)} ORDER BY endpoint_id LIMIT %s",
            values,
        )

    def source_support(self, tenant_id: str, endpoint_id: str, source_id: str) -> bool:
        endpoint = self.get_endpoint(tenant_id, endpoint_id)
        capabilities = endpoint["capabilities"] or {}
        sources = capabilities.get("sources", []) if isinstance(capabilities, dict) else []
        return source_id in sources

    def summarize(self, tenant_id: str) -> dict[str, Any]:
        rows = self.db.query(
            "SELECT platform,state,count(*)::int AS count FROM endpoints "
            "WHERE tenant_id=%s GROUP BY platform,state ORDER BY platform,state",
            (tenant_id,),
        )
        by_platform: dict[str, int] = defaultdict(int)
        by_state: dict[str, int] = defaultdict(int)
        for row in rows:
            by_platform[row["platform"]] += row["count"]
            by_state[row["state"]] += row["count"]
        return {
            "generation": self.generation(tenant_id),
            "endpoint_count": sum(by_platform.values()),
            "platforms": dict(sorted(by_platform.items())),
            "states": dict(sorted(by_state.items())),
        }

    def last_complete_generation(self, tenant_id: str) -> int | None:
        row = self.db.one(
            "SELECT generation_id FROM inventory_generations WHERE tenant_id=%s AND state='complete' "
            "ORDER BY generation_id DESC LIMIT 1",
            (tenant_id,),
        )
        return int(row["generation_id"]) if row else None

    def begin_generation(self, tenant_id: str, required_shards: list[str]) -> int:
        shards = sorted({str(item).strip() for item in required_shards if str(item).strip()})
        if not shards:
            raise InvalidRequest("inventory generation requires at least one shard")
        now = datetime.now(timezone.utc)
        with self.db.transaction("SERIALIZABLE") as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"inventory:{tenant_id}",))
            row = conn.execute(
                "INSERT INTO inventory_generations(tenant_id,state,required_shards,started_at) "
                "VALUES(%s,'collecting',%s,%s) RETURNING generation_id",
                (tenant_id, len(shards), now),
            ).fetchone()
            generation_id = int(row["generation_id"])
            conn.executemany(
                "INSERT INTO inventory_shards(generation_id,shard_id,disposition,updated_at) "
                "VALUES(%s,%s,'pending',%s)",
                [(generation_id, shard, now) for shard in shards],
            )
            return generation_id

    def record_shard(self, generation_id: int, shard_id: str, disposition: str,
                     records: list[dict[str, Any]] | None = None,
                     error_code: str | None = None, error_detail: dict[str, Any] | None = None) -> None:
        if disposition not in {"success", "unsupported", "failed"}:
            raise InvalidRequest("shard disposition must be success, unsupported, or failed")
        if disposition == "success" and records is None:
            raise InvalidRequest("successful shard requires its record set")
        now = datetime.now(timezone.utc)
        normalized: list[dict[str, Any]] = []
        for record in records or []:
            endpoint_id = normalize_endpoint_id(str(record.get("endpoint_id", "")))
            if not record.get("tenant_id") or not record.get("platform") or not record.get("site_id"):
                raise InvalidRequest("inventory record is missing tenant/platform/site identity")
            normalized.append({**record, "endpoint_id": endpoint_id})
        with self.db.transaction("SERIALIZABLE") as conn:
            shard = conn.execute(
                "SELECT disposition FROM inventory_shards WHERE generation_id=%s AND shard_id=%s FOR UPDATE",
                (generation_id, shard_id),
            ).fetchone()
            if shard is None:
                raise NotFound("inventory shard does not belong to this generation")
            if shard["disposition"] != "pending":
                raise Conflict("inventory shard already has a terminal disposition")
            if disposition == "success":
                conn.executemany(
                    "INSERT INTO endpoint_inventory_staging(generation_id,tenant_id,endpoint_id,platform,site_id,state,capabilities,last_seen_at) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(generation_id,tenant_id,endpoint_id) DO UPDATE "
                    "SET platform=EXCLUDED.platform,site_id=EXCLUDED.site_id,state=EXCLUDED.state,capabilities=EXCLUDED.capabilities,last_seen_at=EXCLUDED.last_seen_at",
                    [
                        (generation_id, item["tenant_id"], item["endpoint_id"], item["platform"], item["site_id"],
                         item.get("state", "active"), Jsonb(item.get("capabilities", {})), item.get("last_seen_at", now))
                        for item in normalized
                    ],
                )
            conn.execute(
                "UPDATE inventory_shards SET disposition=%s,record_count=%s,error_code=%s,error_detail=%s,updated_at=%s "
                "WHERE generation_id=%s AND shard_id=%s",
                (disposition, len(normalized), error_code, Jsonb(error_detail or {}), now, generation_id, shard_id),
            )

    def finalize_generation(self, tenant_id: str, generation_id: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with self.db.transaction("SERIALIZABLE") as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"inventory:{tenant_id}",))
            generation = conn.execute(
                "SELECT required_shards,state FROM inventory_generations WHERE tenant_id=%s AND generation_id=%s FOR UPDATE",
                (tenant_id, generation_id),
            ).fetchone()
            if generation is None:
                raise NotFound("inventory generation not found")
            disposition = conn.execute(
                "SELECT count(*) AS total,count(*) FILTER(WHERE inventory_shards.disposition='pending') AS pending, "
                "count(*) FILTER(WHERE inventory_shards.disposition='failed') AS failed, "
                "coalesce(sum(record_count),0) AS records FROM inventory_shards "
                "WHERE generation_id=%s",
                (generation_id,),
            ).fetchone()
            total = int(disposition["total"])
            pending = int(disposition["pending"])
            failed = int(disposition["failed"])
            if total != int(generation["required_shards"]) or pending:
                conn.execute(
                    "UPDATE inventory_generations SET state='incomplete',finalized_at=%s WHERE generation_id=%s",
                    (now, generation_id),
                )
                return {"generation_id": generation_id, "state": "incomplete", "pending_shards": pending, "published": False}
            if failed:
                conn.execute(
                    "UPDATE inventory_generations SET state='incomplete',failed_shards=%s,finalized_at=%s WHERE generation_id=%s",
                    (failed, now, generation_id),
                )
                return {"generation_id": generation_id, "state": "incomplete", "failed_shards": failed, "published": False}
            successful = int(conn.execute("SELECT count(*) AS n FROM inventory_shards WHERE generation_id=%s AND disposition='success'", (generation_id,)).fetchone()["n"])
            unsupported = int(conn.execute("SELECT count(*) AS n FROM inventory_shards WHERE generation_id=%s AND disposition='unsupported'", (generation_id,)).fetchone()["n"])
            conn.execute(
                "INSERT INTO endpoints(endpoint_id,tenant_id,platform,site_id,state,inventory_generation,capabilities,last_seen_at) "
                "SELECT endpoint_id,tenant_id,platform,site_id,state,%s,capabilities,last_seen_at FROM endpoint_inventory_staging "
                "WHERE generation_id=%s ON CONFLICT(tenant_id,endpoint_id) DO UPDATE SET platform=EXCLUDED.platform,site_id=EXCLUDED.site_id,state=EXCLUDED.state,inventory_generation=EXCLUDED.inventory_generation,capabilities=EXCLUDED.capabilities,last_seen_at=EXCLUDED.last_seen_at",
                (generation_id, generation_id),
            )
            conn.execute(
                "UPDATE inventory_generations SET state='complete',successful_shards=%s,unsupported_shards=%s,record_count=%s,finalized_at=%s WHERE generation_id=%s",
                (successful, unsupported, int(disposition["records"]), now, generation_id),
            )
            return {"generation_id": generation_id, "state": "complete", "successful_shards": successful,
                    "unsupported_shards": unsupported, "record_count": int(disposition["records"]), "published": True}

    def generation_status(self, tenant_id: str, generation_id: int) -> dict[str, Any]:
        generation = self.db.one(
            "SELECT generation_id,state,required_shards,successful_shards,unsupported_shards,failed_shards,record_count,started_at,finalized_at "
            "FROM inventory_generations WHERE tenant_id=%s AND generation_id=%s",
            (tenant_id, generation_id),
        )
        if generation is None:
            raise NotFound("inventory generation not found")
        shards = self.db.query(
            "SELECT shard_id,disposition,record_count,error_code,updated_at FROM inventory_shards "
            "WHERE generation_id=%s ORDER BY shard_id",
            (generation_id,),
        )
        return {**generation, "shards": shards}
