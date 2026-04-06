"""Reusable FastAPI dependencies for permission checking."""

from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires the caller to be an admin."""
    if current_user.user_role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


def require_admin_or_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin or teacher role."""
    if current_user.user_role not in (UserRole.admin, UserRole.teacher):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


def require_admin_or_self(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin or the user accessing their own resource."""
    if current_user.user_role != UserRole.admin and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


class ClassPermissionChecker:
    """Reusable permission checker for class-scoped endpoints.

    Usage in endpoint:
        checker = ClassPermissionChecker(allowed_roles=[UserRole.admin, UserRole.teacher])
        def endpoint(..., _=Depends(checker.check(class_id, current_user, db))): ...

    Or call directly:
        ClassPermissionChecker.verify_class_access(db, class_id, current_user, require_teacher=True)
    """

    @staticmethod
    def verify_class_access(
        db: Session,
        class_id: int,
        current_user: User,
        *,
        require_teacher: bool = False,
        allow_enrolled_student: bool = False,
    ) -> "Class":
        """Verify that the current user can access the given class.

        Returns the Class object if access is granted.
        Raises HTTPException otherwise.
        """
        from app.models.classes import Class
        from app.models.user import UserClass

        db_class = db.get(Class, class_id)
        if not db_class:
            raise HTTPException(status_code=404, detail="Class not found")

        if current_user.user_role == UserRole.admin:
            return db_class

        if current_user.user_role == UserRole.teacher:
            if require_teacher and db_class.teacher_id != current_user.user_id:
                raise HTTPException(status_code=403, detail="Not enough permissions")
            return db_class

        if allow_enrolled_student and current_user.user_role == UserRole.student:
            from sqlmodel import select
            enrolled = db.exec(
                select(UserClass).where(
                    (UserClass.class_id == class_id) & (UserClass.user_id == current_user.user_id)
                )
            ).first()
            if enrolled:
                return db_class

        raise HTTPException(status_code=403, detail="Not enough permissions")

    @staticmethod
    def verify_exam_linked_to_class(db: Session, class_id: int, exam_id: int) -> "ClassExam":
        """Verify an exam is linked to a class. Returns the ClassExam link."""
        from sqlmodel import select
        from app.models.exams import ClassExam

        link = db.exec(
            select(ClassExam).where(
                (ClassExam.class_id == class_id) & (ClassExam.exam_id == exam_id)
            )
        ).first()
        if not link:
            raise HTTPException(status_code=404, detail="Exam is not linked to this class")
        return link
