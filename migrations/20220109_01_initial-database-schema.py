"""
Initial database schema
"""

from yoyo import step

__depends__ = {}

steps = [
    step("""
        CREATE TABLE sessions (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_agent VARCHAR(255)
        );""",
        "DROP TABLE sessions"),
    step("""
        CREATE TABLE events (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            name VARCHAR(50),
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            session_id INT,
            properties JSON
        );""",
        "DROP TABLE events")
]
