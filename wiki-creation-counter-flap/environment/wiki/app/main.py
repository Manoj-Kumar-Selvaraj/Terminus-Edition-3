from __future__ import annotations

import sqlite3

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from app.db import connect, ping

# Starter: counters are process-local only and never rebound from tables.
users_created_total = Counter("users_created_total", "Users created")
posts_created_total = Counter("posts_created_total", "Posts created")

app = FastAPI(title="wiki-service")


class UserIn(BaseModel):
    name: str = Field(min_length=1)


class PostIn(BaseModel):
    user_id: int
    content: str = Field(min_length=1)


@app.get("/health/live")
def live() -> dict[str, str]:
    # Starter defect: liveness hits the database (restart loop on flap).
    ping()
    return {"status": "alive"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    try:
        ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database not ready") from exc
    return {"status": "ready"}


@app.get("/health/startup")
def startup() -> dict[str, str]:
    return {"status": "started"}


@app.post("/users")
def create_user(body: UserIn) -> dict:
    con = connect()
    try:
        cur = con.execute(
            "INSERT INTO users(name) VALUES (?)",
            (body.name,),
        )
        con.commit()
        row_id = int(cur.lastrowid)
        users_created_total.inc()
        row = con.execute(
            "SELECT id, name, created_time FROM users WHERE id = ?",
            (row_id,),
        ).fetchone()
        return {"id": row["id"], "name": row["name"], "created_time": row["created_time"]}
    finally:
        con.close()


@app.post("/posts")
def create_post(body: PostIn) -> dict:
    con = connect()
    try:
        try:
            cur = con.execute(
                "INSERT INTO posts(content, user_id) VALUES (?, ?)",
                (body.content, body.user_id),
            )
            con.commit()
        except sqlite3.IntegrityError as exc:
            # Starter defect: FK miss becomes 500-shaped 400/500 instead of 404.
            raise HTTPException(status_code=400, detail="invalid user") from exc
        posts_created_total.inc()
        row = con.execute(
            "SELECT id, content, user_id, created_time FROM posts WHERE id = ?",
            (int(cur.lastrowid),),
        ).fetchone()
        return {
            "id": row["id"],
            "content": row["content"],
            "user_id": row["user_id"],
            "created_time": row["created_time"],
        }
    finally:
        con.close()


@app.get("/users/{user_id}")
@app.get("/user/{user_id}")
def get_user(user_id: int) -> dict:
    con = connect()
    try:
        row = con.execute(
            "SELECT id, name, created_time FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {"id": row["id"], "name": row["name"], "created_time": row["created_time"]}
    finally:
        con.close()


@app.get("/posts/{post_id}")
def get_post(post_id: int) -> dict:
    con = connect()
    try:
        row = con.execute(
            "SELECT id, content, user_id, created_time FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Post not found")
        return {
            "post_id": row["id"],
            "content": row["content"],
            "user_id": row["user_id"],
            "created_time": row["created_time"],
        }
    finally:
        con.close()


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
