#!/bin/bash

PYTHONPATH=${PYTHONPATH:-$(pwd)}
QDRANT_URL=${QDRANT_URL:-"http://localhost:6333"}
QDRANT_API_KEY=${QDRANT_API_KEY:-"test"}
MONGDB_URI=${MONGDB_URI:-"mongodb://10.100.200.119:27017/"}
MONGDB_DB=${MONGDB_DB:-"test"}
DEVICE=${DEVICE:-"cuda:0"}
API_PORT=${API_PORT:-"8000"}


export PYTHONPATH
export QDRANT_URL
export QDRANT_API_KEY
export MONGDB_URI
export MONGDB_DB
export DEVICE
export API_PORT

python src/main.py "$@"
