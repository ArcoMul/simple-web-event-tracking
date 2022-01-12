#!/bin/bash

# Wait for DB
./wait-for-it.sh -t 30 $DB_HOST:$DB_PORT

# Run migrations
yoyo apply --database postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME ./migrations

# Start app
uvicorn main:app --host $HOST --port $PORT --reload