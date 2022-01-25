"""
Initial database schema
"""

from yoyo import step

__depends__ = {}

steps = [
    step("""CREATE EXTENSION IF NOT EXISTS "pgcrypto"; """),
    step(
        """
        CREATE TABLE sessions (
            id UUID DEFAULT gen_random_uuid(),
            created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            user_agent VARCHAR(255)
        );""",
        "DROP TABLE sessions",
    ),
    step(
        """
        CREATE TABLE events (
            id SERIAL PRIMARY KEY,
            session_id UUID,
            created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(50) NOT NULL,
            url VARCHAR(255),
            properties JSON
        );""",
        "DROP TABLE events",
    ),
]
