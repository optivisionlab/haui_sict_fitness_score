from pymongo import MongoClient
from pymongo.errors import PyMongoError
from src.config.configs import MONGDB_URI,MONGDB_DB
from dateutil import parser


class MongoDBManager:
    def __init__(self, uri:str =  MONGDB_URI, db_name: str = MONGDB_DB):
        try:
            self.client = MongoClient(uri)
            self.db = self.client[db_name]
            print(f"✅ Kết nối MongoDB thành công tới database '{db_name}'")
        except PyMongoError as e:
            print(f"❌ Lỗi khi kết nối MongoDB: {e}")
            raise

    def insert_one(self, collection_name: str, document: dict):
        try:
            result = self.db[collection_name].insert_one(document)
            print(f"✅ Đã insert document vào '{collection_name}', id = {result.inserted_id}")
            return result.inserted_id
        except PyMongoError as e:
            print(f"❌ Lỗi insert: {e}")
            return None


    def insert_many(self, collection_name: str, documents: list[dict]):
        try:
            result = self.db[collection_name].insert_many(documents)
            print(f"✅ Insert {len(result.inserted_ids)} documents vào '{collection_name}'")
            return result.inserted_ids
        except PyMongoError as e:
            print(f"❌ Lỗi insert_many: {e}")
            return None

    def delete_collection(self, collection_name: str):
        try:
            self.db[collection_name].drop()
            print(f"✅ Collection '{collection_name}' đã bị xóa")
        except PyMongoError as e:
            print(f"❌ Lỗi khi xóa collection: {e}")

if __name__ == "__main__":
    db = MongoDBManager()
    expiry_date = '2021-07-13T00:00:00.000Z'
    expiry = parser.parse(expiry_date)
    item_3 = {
        "item_name" : "Bread",
        "quantity" : 2,
        "ingredients" : "all-purpose flour",
        "expiry_date" : expiry
    }
    db.insert_one('test', item_3)