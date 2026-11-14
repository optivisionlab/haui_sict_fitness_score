from typing import Any, Optional
from bson import ObjectId

from app.crud.base import CRUDBase
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, email: str) -> Optional[User]:
        """Tìm user theo email."""
        doc = self.collection.find_one({"email": email.strip().lower()})
        if not doc:
            return None
        return self.model.model_validate(doc)

    def get_by_user_code(self, user_code: str) -> Optional[User]:
        """Tìm user theo mã sinh viên / mã nhân viên."""
        doc = self.collection.find_one({"userCode": user_code.strip()})
        if not doc:
            return None
        return self.model.model_validate(doc)

    def get_by_role(
        self,
        role: UserRole | str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[User], int]:
        """Lấy danh sách user theo vai trò."""
        role_value = role.value if isinstance(role, UserRole) else str(role)
        return self.get_multi(filter={"role": role_value}, skip=skip, limit=limit)

    def update_password(self, id: str | ObjectId, hashed_password: str) -> Optional[User]:
        """Cập nhật mật khẩu đã hash."""
        return self.update(id, {"password": hashed_password})

    def update_status(self, id: str | ObjectId, status: str) -> Optional[User]:
        """Cập nhật trạng thái người dùng (active, inactive, blocked)."""
        return self.update(id, {"userStatus": status})


crud_user = CRUDUser(User)
