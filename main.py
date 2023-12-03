import re
import sqlite3
from time import time
from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, status, Security
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader
import config 
app = FastAPI()

# db init
db = sqlite3.connect("minilinks.db")
db.execute(
    "CREATE TABLE IF NOT EXISTS links(id TEXT UNIQUE, url TEXT, note TEXT, created_at INTEGER, updated_at INTEGER)"
)
db.close()


# api key
api_key_header = APIKeyHeader(name="X-Api-key")

def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    if api_key_header == config.SECRET_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key"
    )


@app.get("/{id}")
def redirect(id: str, response: Response):
    with sqlite3.connect("minilinks.db") as db:
        cur = db.execute("SELECT url FROM links WHERE id=?", (id,))
        url = cur.fetchone()[0]
        print(url)
        if url is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found!")
        return RedirectResponse(url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@app.post("/api")
def add(
    request: Request,
    id: str,
    url: str,
    note: str | None = None,
    api_key: str = Security(get_api_key),
):
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
def edit(
    request: Request,
    id: str,
    url: Optional[str] = None,
    note: str | None = None,
    api_key: str = Security(get_api_key),
):
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
def delete(id: str, api_key: str = Security(get_api_key)):
    with sqlite3.connect("minilinks.db") as db:
        cur = db.execute("SELECT * FROM links WHERE id = ?", (id,))
        print(cur.fetchone())
        if cur.fetchone():
            db.execute("DELETE FROM links WHERE EXISTS(SELECT * FROM links WHERE id = ?)", (id,))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL not found")
    return {"deleted_id": id}


if __name__ == "__main__":
    uvicorn.run(app, port=8000,)
