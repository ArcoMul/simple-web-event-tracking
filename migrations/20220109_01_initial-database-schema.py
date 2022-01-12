"""
Initial database schema
"""

from yoyo import step

__depends__ = {}

steps = [
    step("""
        CREATE TABLE sessions (
            id SERIAL PRIMARY KEY,
            created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            user_agent VARCHAR(255)
        );""",
        "DROP TABLE sessions"),
    step("""
        CREATE TABLE events (
            id SERIAL PRIMARY KEY,
            session_id INT,
            created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(50) NOT NULL,
            url VARCHAR(255),
            properties JSON
        );""",
        "DROP TABLE events")
]
