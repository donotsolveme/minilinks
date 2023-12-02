import re
import sqlite3
from time import time
from typing import Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI()

db = sqlite3.connect("minilinks.db")
db.execute(
    "CREATE TABLE IF NOT EXISTS links(id TEXT UNIQUE, url TEXT, note TEXT, created_at INTEGER, updated_at INTEGER)"
)
db.close()


@app.get("/{id}")
def redirect(id: str, response: Response):
    with sqlite3.connect("minilinks.db") as db:
        cur = db.execute("SELECT url FROM links WHERE id=?", (id,))
        url = cur.fetchone()[0]
        print(url)
        if url is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return "Link not found!"
        return RedirectResponse(url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@app.post("/api")
def add(request: Request, id: str, url: str, note: str | None = None):
    if re.match(url, r"^\w+:\/\/") is None:
        url = "http://" + url
    with sqlite3.connect("minilinks.db") as db:
        now = int(time())
        db.execute(
            "INSERT INTO links VALUES(?, ?, ?, ?, ?)",
            (
                id,
                url,
                note,
                now,  # created_at
                now,  # updated_at
            ),
        )
        db.commit()
    resp = {
        "id": id,
        "url": f"{request.base_url}{id}",
        "orig_url": url,
        "note": note,
        "created_at": now,
        "updated_at": now,
    }
    return resp


@app.patch("/api")
def edit(request: Request, id: str, url: Optional[str] = None, note: str | None = None):
    with sqlite3.connect("minilinks.db") as db:
        if url is not None:
            db.execute("UPDATE links SET url = ? WHERE id = ?", (url, id))
        if note is not None:
            db.execute("UPDATE links SET note = ? WHERE id = ?", (note, id))
        now = int(time())
        db.execute(
            "UPDATE links SET updated_at = ? WHERE id = ?",
            (
                now,
                id,
            ),
        )
        cur = db.execute("SELECT * FROM links WHERE id = ?", (id,))
        after = cur.fetchone()

    resp = {
        "id": id,
        "url": f"{request.base_url}{id}",
        "orig_url": after[1],
        "note": after[2],
        "created_at": after[3],
        "updated_at": after[4],
    }
    return resp


@app.delete("/api")
def delete(id: str):
    with sqlite3.connect("minilinks.db") as db:
        db.execute("DELETE FROM links WHERE id = ?", (id))
    return {"deleted_id": id}
