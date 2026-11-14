from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from bson import ObjectId
from pydantic import BaseModel
from pymongo import ReturnDocument
from pymongo.collection import Collection

from app.core.database import get_db
from app.models.base import BaseDocument

ModelType = TypeVar("ModelType", bound=BaseDocument)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


def to_object_id(id_val: Any) -> Optional[ObjectId]:
    """Chuyển đổi an toàn giá trị string sang BSON ObjectId."""
    if isinstance(id_val, ObjectId):
        return id_val
    if isinstance(id_val, str) and ObjectId.is_valid(id_val):
        return ObjectId(id_val)
    return None


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic CRUD operations cho MongoDB documents."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    @property
    def collection(self) -> Collection:
        collection_name = getattr(self.model, "__collection__", "")
        if not collection_name:
            raise ValueError(f"Model {self.model.__name__} chưa định nghĩa __collection__")
        return get_db()[collection_name]

    def get(self, id: str | ObjectId) -> Optional[ModelType]:
        """Lấy 1 document theo ID."""
        oid = to_object_id(id)
        if oid is None:
            return None
        doc = self.collection.find_one({"_id": oid})
        if not doc:
            return None
        return self.model.model_validate(doc)

    def get_multi(
        self,
        filter: Optional[dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[list[tuple[str, int]]] = None,
    ) -> tuple[list[ModelType], int]:
        """Lấy danh sách documents có filter, phân trang và sắp xếp. Trả về (items, total_count)."""
        query = filter or {}
        total = self.collection.count_documents(query)

        cursor = self.collection.find(query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        else:
            cursor = cursor.sort("createdAt", -1)

        items = [self.model.model_validate(doc) for doc in cursor]
        return items, total

    def create(self, obj_in: CreateSchemaType | ModelType | dict[str, Any]) -> ModelType:
        """Thêm mới 1 document vào MongoDB."""
        now = datetime.now(timezone.utc)

        if isinstance(obj_in, BaseModel):
            # Dump theo camelCase alias và bỏ các giá trị chưa set
            doc = obj_in.model_dump(by_alias=True, exclude_unset=True)
        else:
            doc = dict(obj_in)

        # Xử lý ID
        if "_id" in doc:
            if doc["_id"] is None:
                doc.pop("_id")
            elif isinstance(doc["_id"], str) and ObjectId.is_valid(doc["_id"]):
                doc["_id"] = ObjectId(doc["_id"])
        elif "id" in doc:
            doc.pop("id", None)

        # Set timestamps
        doc.setdefault("createdAt", now)
        doc.setdefault("updatedAt", now)

        result = self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self.model.model_validate(doc)

    def update(
        self,
        id: str | ObjectId,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> Optional[ModelType]:
        """Cập nhật 1 document theo ID."""
        oid = to_object_id(id)
        if oid is None:
            return None

        if isinstance(obj_in, BaseModel):
            update_data = obj_in.model_dump(by_alias=True, exclude_unset=True)
        else:
            update_data = dict(obj_in)

        # Tránh cập nhật ID
        update_data.pop("_id", None)
        update_data.pop("id", None)

        if not update_data:
            return self.get(oid)

        update_data["updatedAt"] = datetime.now(timezone.utc)

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def delete(self, id: str | ObjectId) -> bool:
        """Xóa 1 document theo ID."""
        oid = to_object_id(id)
        if oid is None:
            return False
        result = self.collection.delete_one({"_id": oid})
        return result.deleted_count > 0

    def exists(self, id: str | ObjectId) -> bool:
        """Kiểm tra document có tồn tại hay không."""
        oid = to_object_id(id)
        if oid is None:
            return False
        return self.collection.count_documents({"_id": oid}, limit=1) > 0

    def count(self, filter: Optional[dict[str, Any]] = None) -> int:
        """Đếm số lượng documents theo filter."""
        return self.collection.count_documents(filter or {})
