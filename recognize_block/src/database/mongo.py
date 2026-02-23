from pymongo import MongoClient
from pymongo.errors import PyMongoError
from src.config.config import MONGO_URI,MONGO_DB
from dateutil import parser
from loguru import logger
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult
from typing import Optional, Any, List, Optional


class MongoDBManager:
    def __init__(self, uri: str = MONGO_URI, db_name: str = MONGO_DB):
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            self.db = self.client[db_name]
            logger.info(f"✅ Kết nối MongoDB thành công tới database '{db_name}'")
        except PyMongoError as e:
            logger.error(f"❌ Lỗi khi kết nối MongoDB: {e}")
            raise


    def insert_one(self, collection: str, document: dict) -> Optional[str]:
        try:
            result: InsertOneResult = self.db[collection].insert_one(document)
            logger.info(f"✅ Insert 1 document vào '{collection}', id={result.inserted_id}")
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error(f"❌ Lỗi insert_one vào '{collection}': {e}")
            return None


    def insert_many(self, collection: str, documents: list[dict]) -> Optional[list[str]]:
        try:
            result: InsertManyResult = self.db[collection].insert_many(documents)
            logger.info(f"✅ Insert {len(result.inserted_ids)} documents vào '{collection}'")
            return [str(_id) for _id in result.inserted_ids]
        except PyMongoError as e:
            logger.error(f"❌ Lỗi insert_many vào '{collection}': {e}")
            return None


    def upsert(self, collection: str, filter_doc: dict, update_doc: dict) -> UpdateResult:
        try:
            result = self.db[collection].update_one(
                filter_doc, update_doc, upsert=True
            )
            logger.info(
                f"✅ Upsert vào '{collection}': matched={result.matched_count}, "
                f"modified={result.modified_count}, upserted_id={result.upserted_id}"
            )
            return result
        except PyMongoError as e:
            logger.error(f"❌ Lỗi upsert vào '{collection}': {e}")
            raise


    def find_one(self, collection: str, filter_doc: dict) -> Optional[dict]:
        try:
            return self.db[collection].find_one(filter_doc)
        except PyMongoError as e:
            logger.error(f"❌ Lỗi find_one từ '{collection}': {e}")
            return None


    def find_all(self, collection: str, filter_doc: Optional[dict] = None) -> List[dict]:
        """Lấy tất cả document trong collection (hoặc theo filter)."""
        filter_doc = filter_doc or {}
        try:
            docs = list(self.db[collection].find(filter_doc))
            # Chuyển ObjectId sang string nếu cần
            for d in docs:
                if "_id" in d:
                    d["_id"] = str(d["_id"])
            return docs
        except PyMongoError as e:
            logger.error(f"❌ Lỗi find_all từ '{collection}': {e}")
            return []


    def delete_collection(self, collection: str) -> bool:
        try:
            self.db[collection].drop()
            logger.info(f"✅ Collection '{collection}' đã bị xóa")
            return True
        except PyMongoError as e:
            logger.error(f"❌ Lỗi khi xóa collection '{collection}': {e}")
            return False


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