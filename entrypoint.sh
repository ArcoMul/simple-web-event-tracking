#!/bin/bash

# Wait for DB
./wait-for-it.sh -t 30 $POSTGRES_HOST:$POSTGRES_PORT

# Run migrations
yoyo apply --database postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$DB_NAME ./migrations

# Start app
uvicorn main:app --host $HOST --port $PORT --reload