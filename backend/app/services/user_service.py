from typing import Optional
from fastapi import HTTPException, status

from app.crud.user import crud_user
from app.models.user import User, UserRole
from app.schemas.user import Token, UserCreate, UserLogin, UserRead, UserUpdate
from app.services.auth_service import create_access_token, hash_password, verify_password


class UserService:
    def register(self, user_in: UserCreate) -> User:
        """Đăng ký tài khoản mới."""
        existing_user = crud_user.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được sử dụng trong hệ thống",
            )

        if user_in.user_code:
            existing_code = crud_user.get_by_user_code(user_in.user_code)
            if existing_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mã người dùng '{user_in.user_code}' đã tồn tại",
                )

        # Hash password
        user_dict = user_in.model_dump(by_alias=True, exclude_unset=True)
        user_dict["password"] = hash_password(user_in.password)

        return crud_user.create(user_dict)

    def login(self, login_data: UserLogin) -> tuple[User, Token]:
        """Đăng nhập hệ thống."""
        user = crud_user.get_by_email(login_data.email)
        if not user or not verify_password(login_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác",
            )

        if user.user_status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị khóa",
            )

        access_token = create_access_token({
            "sub": str(user.id),
            "role": user.role.value,
            "email": user.email,
        })
        token = Token(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        )
        return user, token

    def get_by_id(self, user_id: str) -> User:
        """Lấy thông tin người dùng theo ID."""
        user = crud_user.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người dùng",
            )
        return user

    def update_profile(self, user_id: str, user_in: UserUpdate) -> User:
        """Cập nhật thông tin tài khoản."""
        user = self.get_by_id(user_id)

        update_data = user_in.model_dump(by_alias=True, exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["password"] = hash_password(update_data["password"])

        if "email" in update_data and update_data["email"] != user.email:
            existing = crud_user.get_by_email(update_data["email"])
            if existing and str(existing.id) != str(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email đã tồn tại trong hệ thống",
                )

        updated = crud_user.update(user_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cập nhật thông tin thất bại",
            )
        return updated

    def get_users(
        self,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[User], int]:
        """Lấy danh sách người dùng có phân trang."""
        if role:
            return crud_user.get_by_role(role, skip=skip, limit=limit)
        return crud_user.get_multi(skip=skip, limit=limit)

    def delete_user(self, user_id: str) -> bool:
        """Xóa người dùng."""
        self.get_by_id(user_id)
        return crud_user.delete(user_id)


user_service = UserService()
