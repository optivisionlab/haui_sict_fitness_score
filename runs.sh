export PYTHONPATH=$(pwd)
export QDRANT_URL="http://localhost:6333"
export MONGDB_URI="mongodb://root:example@localhost:27017/admin"
export MONGDB_DB="test"

python src/main.py