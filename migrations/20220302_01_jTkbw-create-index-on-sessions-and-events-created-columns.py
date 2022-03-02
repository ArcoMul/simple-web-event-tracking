"""
Create index on sessions and events created columns
"""

from yoyo import step

__depends__ = {'20220109_01_initial-database-schema'}

steps = [
    step("CREATE INDEX sessions_created_brin_index ON sessions USING BRIN (created);"),
    step("CREATE INDEX events_created_brin_index ON events USING BRIN (created);")
]
