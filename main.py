import os
from typing import Optional, Any
import base64
import json
import secrets

from fastapi import Cookie, FastAPI, HTTPException, Header, Request, Depends, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import psycopg2
from psycopg2.extras import RealDictCursor

from crawlerdetect import CrawlerDetect

import yaml

config: Any = {}

try:
    with open("config.yml") as file:
        try:
            config = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(exc)
except FileNotFoundError as err:
    print("No config.yml found")

if not config:
    config = {}

print("config", config)

blocked_ips: "list[str]" = []
if "blocked_ips" in config:
    blocked_ips = config["blocked_ips"] if config["blocked_ips"] != None else []

crawler_detect = CrawlerDetect()


username = os.environ["USERNAME"]
password = os.environ["PASSWORD"]


connection = psycopg2.connect(
    host=os.environ["POSTGRES_HOST"],
    user=os.environ["POSTGRES_USER"],
    port=os.environ["POSTGRES_PORT"],
    password=os.environ["POSTGRES_PASSWORD"],
    database=os.environ["DB_NAME"],
)
connection.set_session(autocommit=True)


app = FastAPI()

security = HTTPBasic()


def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, username)
    correct_password = secrets.compare_digest(credentials.password, password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


def create_session(user_agent: Optional[str]) -> Optional[str]:
    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO sessions (user_agent) VALUES (%s) RETURNING id"
            cursor.execute(query, (user_agent,))
            session_id = cursor.fetchone()[0]
        return session_id
    except:
        connection.rollback()
        return None


def insert_event(session_id: str, json_data: dict, first_event: bool) -> None:
    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO events (name, session_id, first_event, url, properties) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(
                query,
                (
                    json_data["name"],
                    session_id,
                    first_event,
                    json_data["url"],
                    json.dumps(json_data["properties"]),
                ),
            )
    except:
        connection.rollback()


@app.get("/")
def get_root():
    return {"Hello": "World"}


@app.get("/image")
def get_image(
    request: Request,
    d: str,
    user_agent: Optional[str] = Header(None),
    s_id: Optional[str] = Cookie(None),
):
    response = FileResponse('static/simple-image.jpg')
    # Block crawlers
    if crawler_detect.isCrawler(user_agent):
        print("ignored crawler")
        return response

    # Block certain ips
    ip = request.client.host
    if ip in blocked_ips:
        print("blocked ip", ip)
        return response

    # Get data from query parameter
    data: bytes = base64.b64decode(d)
    if len(data) > 1024:
        print("ERROR: received more than 1024 characters as event json payload")
        return response

    # Convert json string to dict
    json_data = json.loads(data)

    # Create session if visitor doesn't have a cookie yet
    first_event = False
    if not s_id:
        first_event = True
        s_id = create_session(user_agent)

    if not s_id:
        print("error creating session")
        return response

    # Create event
    insert_event(s_id, json_data, first_event)

    # Send response with session cookie
    response.set_cookie(
        key="s_id", value=str(s_id), samesite="None", secure=True, max_age=1073741823
    )
    return response


@app.get("/events")
def get_events(isAuthed=Depends(check_auth)):
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """SELECT * FROM events"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/sessions")
def get_sessions(isAuthed=Depends(check_auth)):
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """SELECT * FROM sessions"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/reset-all")
def get_reset_all(isAuthed=Depends(check_auth)):
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """TRUNCATE TABLE sessions; TRUNCATE TABLE events"""
        cursor.execute(query)
    return JSONResponse({"success": True})


@app.get("/reset-events")
def get_reset_events(isAuthed=Depends(check_auth)):
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """TRUNCATE TABLE events"""
        cursor.execute(query)
    return JSONResponse({"success": True})


@app.get("/use-cases/most-visited-urls")
def get_most_visited_urls(isAuthed=Depends(check_auth)):
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        query = """SELECT url, COUNT(*) as count FROM events GROUP BY url ORDER BY count DESC"""
        cursor.execute(query)
        results = cursor.fetchall()
    return results


@app.get("/use-cases/most-visited-pages")
def get_most_visited_pages(isAuthed=Depends(check_auth)):
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
def get_product_page_conversion(isAuthed=Depends(check_auth)):
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
def get_bounce_rate(isAuthed=Depends(check_auth)):
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
