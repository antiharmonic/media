#!/bin/bash

# add this to local .git/hooks for rebuilding/deploying on commit

docker-compose down
docker-compose build
docker-compose up -d
