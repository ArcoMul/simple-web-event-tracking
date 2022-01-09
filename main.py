from typing import Optional
import base64
import json

from fastapi import Cookie, FastAPI, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import pymysql
from pymysql import cursors


connection = pymysql.connect(
    host="mariadb",
    port=3306,
    user="testuser",
    password="testpassword",
    database="simple-web-event-tracking",
    charset="utf8mb4",
    cursorclass=cursors.DictCursor,
)


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def create_session(user_agent) -> int:
    with connection.cursor() as cursor:
        query = "INSERT INTO `sessions` (`user_agent`) VALUES (%s)"
        cursor.execute(query, (user_agent,))
    connection.commit()
    return cursor.lastrowid


def insert_event(session_id, json_data):
    with connection.cursor() as cursor:
        query = "INSERT INTO `events` (`name`, `session_id`, `properties`) VALUES (%s, %s, %s)"
        cursor.execute(
            query, (json_data["name"], session_id, json.dumps(json_data["properties"]))
        )
    connection.commit()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/image")
def read_image(
    d: str, user_agent: Optional[str] = Header(None), s_id: Optional[int] = Cookie(None)
):
    data = base64.b64decode(d)
    json_data = json.loads(data)
    print(json_data)
    if not s_id:
        s_id = create_session(user_agent)
    if json_data["type"] == "event":
        insert_event(s_id, json_data)
    response = JSONResponse({"success": True})
    response.set_cookie(key="s_id", value=str(s_id))
    return response


@app.get("/events")
def read_events():
    with connection.cursor() as cursor:
        query = """SELECT * FROM `events`"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/sessions")
def read_sessions():
    with connection.cursor() as cursor:
        query = """SELECT * FROM `sessions`"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results
