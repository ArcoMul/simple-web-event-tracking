"""
Create index on sessions and events created columns
"""

from yoyo import step

__depends__ = {'20220109_01_initial-database-schema'}
__transactional__ = False

steps = [
    step(
        "CREATE INDEX CONCURRENTLY sessions_created_brin_index ON sessions USING BRIN (created);",
        "DROP INDEX sessions_created_brin_index;"
    ),
    step(
        "CREATE INDEX CONCURRENTLY events_created_brin_index ON events USING BRIN (created);",
        "DROP INDEX events_created_brin_index;"
    )
]
