"""PostgreSQL migration runner for Sovereign RDS Control Plane."""
from pathlib import Path
from rds import database
from rds.errors import DatabaseError

MIGRATION_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"

def available_migrations() -> list[tuple[int, str, str]]:
    """Load versioned SQL migration files."""
    migrations = []
    for path in sorted(MIGRATION_DIR.glob("*.sql")):
        prefix, separator, _ = path.name.partition("_")
        if not separator or not prefix.isdigit():
            raise DatabaseError(f"Invalid migration filename: {path.name}")
        migrations.append((int(prefix), path.name, path.read_text(encoding="utf-8")))
    if not migrations:
        raise DatabaseError(f"No migrations found in {MIGRATION_DIR}")
    return migrations

async def run_migrations(database_url: str) -> None:
    """Run migrations in transaction."""
    await database.init_database(database_url)
    async with database.transaction() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                migration_name TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

    for version, name, sql in available_migrations():
        async with database.transaction() as conn:
            cursor = await conn.execute(
                "SELECT migration_name FROM schema_migrations WHERE version = %s",
                (version,),
            )
            row = await cursor.fetchone()
            if row:
                if row["migration_name"] != name:
                    raise DatabaseError(f"Migration version {version} mismatch")
                continue
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations (version, migration_name) VALUES (%s, %s)",
                (version, name),
            )
            print(f"Applied migration {name}")
