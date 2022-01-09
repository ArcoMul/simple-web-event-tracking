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
            session_id INT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(50) NOT NULL,
            url VARCHAR(255),
            properties JSON
        );""",
        "DROP TABLE events")
]
