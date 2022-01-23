#!/bin/bash

echo "Start building Docker image"
docker build -f Dockerfile -t lumocra/simple-web-event-tracking:latest .
echo "Finished building Docker image"

echo "Start pushing Docker image"
docker push lumocra/simple-web-event-tracking:latest
echo "Finished pushing Docker image"
