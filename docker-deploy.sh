#!/bin/bash

# called from .githooks/post-commit, add that script to .git/hooks if you want this to run after a commit

docker-compose down
docker-compose build
docker-compose up -d
