import re
import sqlite3
from time import time
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Security, status
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader

import config

app = FastAPI()

# db init
db = sqlite3.connect("minilinks.db")
db.execute(
    "CREATE TABLE IF NOT EXISTS links(id TEXT UNIQUE, url TEXT, note TEXT, created_at INTEGER, updated_at INTEGER, clicks INTEGER)"
)
db.close()


# api key
api_key_header = APIKeyHeader(name="X-Api-key")


def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    if api_key_header == config.SECRET_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key."
    )


def add_http(url: str) -> str:
    if re.match(r"^\w+:\/\/", url) is None:
        return "http://" + url
    return url


@app.get("/{id}")
def redirect(id: str, response: Response):
    with sqlite3.connect("minilinks.db") as db:
        cur = db.execute("SELECT url FROM links WHERE id=?", (id,))
        try:
            url = cur.fetchone()[0]
        except TypeError:
            response.status_code = status.HTTP_404_NOT_FOUND
            return "Link not found."
        db.execute("UPDATE links SET clicks = clicks + 1 WHERE id = ?", (id,))
        db.commit()
    return RedirectResponse(url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@app.post("/api")
def add(
    request: Request,
    id: str,
    url: str,
    note: str | None = None,
    api_key: str = Security(get_api_key),
):
    url = add_http(url)
    if re.match(r"^https?:\/\/[a-zA-Z1-9-._~]+$", id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID contains illegal characters.",
        )
    with sqlite3.connect("minilinks.db") as db:
        now = int(time())
        try:
            db.execute(
                "INSERT INTO links VALUES(?, ?, ?, ?, ?, ?)",
                (
                    id,
                    url,
                    note,
                    now,  # created_at
                    now,  # updated_at
                    0,  # clicks
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="That ID is in use."
            )
        db.commit()
    resp = {
        "id": id,
        "url": f"{request.base_url}{id}",
        "orig_url": url,
        "note": note,
        "created_at": now,
        "updated_at": now,
        "clicks": 0,
    }
    return resp


@app.patch("/api")
def update(
    request: Request,
    id: str,
    url: Optional[str] = None,
    note: str | None = None,
    api_key: str = Security(get_api_key),
):
    with sqlite3.connect("minilinks.db") as db:
        if url is not None:
            url = add_http(url)
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
        "clicks": after[5],
    }
    return resp


@app.delete("/api")
def delete(id: str, api_key: str = Security(get_api_key)):
    with sqlite3.connect("minilinks.db") as db:
        cur = db.execute("SELECT * FROM links WHERE id = ?", (id,))
        data = cur.fetchone()
        if data is not None:
            db.execute(
                "DELETE FROM links WHERE id = ?",
                (id,),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="URL not found."
            )
    return {"deleted_id": id}


if __name__ == "__main__":
    uvicorn.run(app, port=config.PORT)
