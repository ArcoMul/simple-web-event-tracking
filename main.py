import os
from typing import Optional
import base64
import json

from fastapi import Cookie, FastAPI, Header
from fastapi.responses import JSONResponse

import psycopg2
from psycopg2.extras import RealDictCursor

from crawlerdetect import CrawlerDetect


crawler_detect = CrawlerDetect()


connection = psycopg2.connect(
    host=os.environ['POSTGRES_HOST'],
    user=os.environ['POSTGRES_USER'],
    port=os.environ['POSTGRES_PORT'],
    password=os.environ['POSTGRES_PASSWORD'],
    database=os.environ['DB_NAME'],
)


app = FastAPI()


def create_session(user_agent: Optional[str]) -> str:
    with connection.cursor() as cursor:
        query = "INSERT INTO sessions (user_agent) VALUES (%s) RETURNING id"
        cursor.execute(query, (user_agent,))
        session_id = cursor.fetchone()[0]
    connection.commit()
    return session_id


def insert_event(session_id: str, json_data: dict) -> None:
    with connection.cursor() as cursor:
        query = "INSERT INTO events (name, session_id, url, properties) VALUES (%s, %s, %s, %s)"
        cursor.execute(
            query,
            (
                json_data["name"],
                session_id,
                json_data["url"],
                json.dumps(json_data["properties"]),
            ),
        )
    connection.commit()


@app.get("/")
def get_root():
    return {"Hello": "World"}


@app.get("/image")
def get_image(
    d: str, user_agent: Optional[str] = Header(None), s_id: Optional[str] = Cookie(None)
):
    # Block crawlers
    if crawler_detect.isCrawler(user_agent):
        return JSONResponse()

    # Get data from query parameter
    data: bytes = base64.b64decode(d)
    if len(data) > 1024:
        print("ERROR: received more than 1024 characters as event json payload")
        return JSONResponse()

    # Convert json string to dict
    json_data = json.loads(data)

    # Create session if visitor doesn't have a cookie yet
    if not s_id:
        s_id = create_session(user_agent)

    # Create event
    insert_event(s_id, json_data)

    # Send response with session cookie
    response = JSONResponse({"success": True})
    response.set_cookie(key="s_id", value=str(s_id), samesite="None", secure=True)
    return response


@app.get("/events")
def get_events():
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """SELECT * FROM events"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/sessions")
def get_sessions():
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """SELECT * FROM sessions"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/reset")
def get_reset():
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """TRUNCATE TABLE sessions; TRUNCATE TABLE events"""
        cursor.execute(query)
    return JSONResponse({"success": True})


@app.get("/use-cases/most-visited-urls")
def get_most_visited_urls():
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """SELECT url, COUNT(*) as count FROM events GROUP BY url ORDER BY count DESC"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/use-cases/most-visited-pages")
def get_most_visited_pages():
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
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
def get_product_page_conversion():
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        # Simple - visitors entering the funnel in a later step also get counted
        query = """
            SELECT
                properties->>'page' as step,
                COUNT(DISTINCT session_id) as value
            FROM events
            WHERE properties->>'page' = 'product-detail' OR properties->>'page' = 'checkout'
            GROUP BY properties->>'page'
            ORDER BY value DESC
        """

        # Accurate - only visitors entering the funnel at the start
        query = """
            SELECT
                unnest(array['index', 'product', 'checkout']) as step,
                unnest(array[
                    COUNT(DISTINCT index.session_id),
                    COUNT(DISTINCT product.session_id),
                    COUNT(DISTINCT checkout.session_id)
                ]) as value
            FROM events AS index
            LEFT JOIN events AS product
                ON product.session_id = index.session_id 
                AND product.properties->>'page' = 'product-detail'
                AND product.created > index.created
            LEFT JOIN events AS checkout
                ON checkout.session_id = index.session_id 
                AND checkout.properties->>'page' = 'checkout'
                AND checkout.created > product.created
            WHERE index.name = 'page' AND index.properties->>'page' = 'index'
        """
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/use-cases/bounce-rate")
def get_bounce_rate():
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """
            SELECT 
                properties->>'page' as page,
                COUNT(id) AS total,
                COUNT(DISTINCT events.session_id) AS unique,
                COUNT(sessions.session_id) AS bounces
            FROM events
            LEFT JOIN (
                /* Get sessions and the number of pages visited */
                SELECT session_id, COUNT(id) as count
                FROM events
                GROUP BY session_id
            ) as sessions ON sessions.session_id = events.session_id AND sessions.count = 1
            WHERE name = 'page'
            GROUP BY properties->>'page'
            ORDER BY total DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
    return results
