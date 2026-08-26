"""Database connection and pool management for Sovereign RDS Control Plane."""
import asyncio
from contextlib import asynccontextmanager
import psycopg
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from rds.errors import DatabaseError

_connection_pool = None

async def init_database(database_url: str):
    """Initialize database connection pool."""
    global _connection_pool
    try:
        _connection_pool = AsyncConnectionPool(
            database_url,
            min_size=2,
            max_size=20,
            kwargs={"row_factory": dict_row},
            open=False
        )
        await _connection_pool.open()
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database pool: {e}")

@asynccontextmanager
async def get_connection():
    """Get database connection from pool."""
    if _connection_pool is None:
        raise DatabaseError("Database pool not initialized")
    async with _connection_pool.connection() as conn:
        yield conn

@asynccontextmanager
async def transaction():
    """Get transactional connection."""
    async with get_connection() as conn:
        async with conn.transaction():
            yield conn

async def execute_query(query: str, params: tuple = None):
    """Execute SQL query and return all rows."""
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params or ())
            try:
                return await cur.fetchall()
            except psycopg.ProgrammingError:
                return None

async def execute_one(query: str, params: tuple = None):
    """Execute SQL query and return first row."""
    results = await execute_query(query, params)
    return results[0] if results else None

async def execute_modify(query: str, params: tuple = None):
    """Execute SQL modification query."""
    async with transaction() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params or ())
            return cur.rowcount

async def close_database():
    """Close connection pool."""
    global _connection_pool
    if _connection_pool:
        await _connection_pool.close()
        _connection_pool = None
