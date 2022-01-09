from typing import Optional
import base64
import json

from fastapi import Cookie, FastAPI, Header
from fastapi.responses import JSONResponse

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


def create_session(user_agent) -> int:
    with connection.cursor() as cursor:
        query = "INSERT INTO `sessions` (`user_agent`) VALUES (%s)"
        cursor.execute(query, (user_agent,))
    connection.commit()
    return cursor.lastrowid


def insert_event(session_id, json_data):
    with connection.cursor() as cursor:
        query = "INSERT INTO events (name, session_id, url, properties) VALUES (%s, %s, %s, %s)"
        cursor.execute(
            query, (json_data["name"], session_id, json_data['url'], json.dumps(json_data["properties"]))
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
    insert_event(s_id, json_data)
    response = JSONResponse({"success": True})
    response.set_cookie(key="s_id", value=str(s_id), samesite='None')
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


@app.get("/use-cases/most-visited-urls")
def most_visited_urls():
    with connection.cursor() as cursor:
        query = """SELECT url, COUNT(*) as count FROM events GROUP BY url ORDER BY count DESC"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results

@app.get("/use-cases/most-visited-pages")
def most_visited_pages():
    with connection.cursor() as cursor:
        query = """SELECT JSON_UNQUOTE(JSON_EXTRACT(properties, "$.page")) as page, COUNT(*) as count FROM events GROUP BY JSON_EXTRACT(properties, "$.page") ORDER BY count DESC"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results

@app.get("/use-cases/product-page-conversion")
def product_page_conversion():
    with connection.cursor() as cursor:
        query = """
            SELECT DISTINCT
                JSON_UNQUOTE(JSON_EXTRACT(events.properties, "$.page")) as page,
                COUNT(events.id) as product_detail_count,
                COUNT(after.id) as checkout_count,
                COUNT(after.id) / COUNT(events.id) as conversion
            FROM events
            LEFT JOIN events as after
            ON after.session_id = events.session_id
                AND after.created > events.created
                AND JSON_UNQUOTE(JSON_EXTRACT(after.properties, "$.page")) = "checkout"
            WHERE JSON_UNQUOTE(JSON_EXTRACT(events.properties, "$.page")) = "product-detail"
            GROUP BY JSON_EXTRACT(events.properties, "$.page")"""
        query = """
            SELECT
                'conversion' as label,
                COUNT(DISTINCT product_page.session_id) as product_detail_count,
                COUNT(DISTINCT checkout_page.session_id) as checkout_count
            FROM sessions
            LEFT JOIN events as product_page
                ON product_page.session_id = sessions.id
                AND JSON_UNQUOTE(JSON_EXTRACT(product_page.properties, "$.page")) = "product-detail"
            LEFT JOIN events as checkout_page
                ON checkout_page.session_id = sessions.id
                AND JSON_UNQUOTE(JSON_EXTRACT(checkout_page.properties, "$.page")) = "checkout"
                AND checkout_page.created > product_page.created
            GROUP BY label"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results
