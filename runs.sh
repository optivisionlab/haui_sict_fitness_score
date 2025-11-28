export PYTHONPATH=$(pwd)
export QDRANT_URL="http://localhost:6333"
export MONGDB_URI="mongodb://10.100.200.119:27017/"
export MONGDB_DB="test"
export DEVICE="cuda:0"


python src/main.py
