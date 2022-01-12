from typing import Optional
import base64
import json

from fastapi import Cookie, FastAPI, Header
from fastapi.responses import JSONResponse

import psycopg2


connection = psycopg2.connect(
    host="postgres",
    database="simple-web-event-tracking",
    user="postgres",
    password="testpassword")


app = FastAPI()


def create_session(user_agent) -> int:
    with connection.cursor() as cursor:
        query = "INSERT INTO sessions (user_agent) VALUES (%s) RETURNING id"
        cursor.execute(query, (user_agent,))
        session_id = cursor.fetchone()[0]
    connection.commit()
    print('create_session session_id', session_id)
    return session_id


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
        query = """SELECT * FROM events"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/sessions")
def read_sessions():
    with connection.cursor() as cursor:
        query = """SELECT * FROM sessions"""
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
        query = """
            SELECT properties->>'page' as page, COUNT(*) as count
            FROM events
            GROUP BY properties->>'page'
            ORDER BY count DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
    return results

@app.get("/use-cases/product-page-conversion")
def product_page_conversion():
    with connection.cursor() as cursor:
        query = """
            SELECT
                'conversion' as label,
                COUNT(DISTINCT product_page.session_id) as product_detail_count,
                COUNT(DISTINCT checkout_page.session_id) as checkout_count,
                COUNT(DISTINCT checkout_page.session_id)::decimal / COUNT(DISTINCT product_page.session_id)::decimal as conversion
            FROM sessions
            LEFT JOIN events as product_page
                ON product_page.session_id = sessions.id
                AND product_page.properties->>'page' = 'product-detail'
            LEFT JOIN events as checkout_page
                ON checkout_page.session_id = sessions.id
                AND checkout_page.properties->>'page' = 'checkout'
                AND checkout_page.created > product_page.created
            GROUP BY label"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results
