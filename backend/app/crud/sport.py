from typing import Optional

from app.crud.base import CRUDBase
from app.models.sport import Sport, SportMode
from app.schemas.sport import SportCreate, SportUpdate


class CRUDSport(CRUDBase[Sport, SportCreate, SportUpdate]):
    def get_by_code(self, code: str) -> Optional[Sport]:
        """Tìm môn thể thao theo mã code (unique)."""
        doc = self.collection.find_one({"code": code.strip().lower()})
        if not doc:
            return None
        return self.model.model_validate(doc)

    def get_by_mode(
        self,
        mode: SportMode | str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Sport], int]:
        """Lấy danh sách các môn theo hình thức chấm (video / camera)."""
        mode_val = mode.value if isinstance(mode, SportMode) else str(mode)
        return self.get_multi(filter={"mode": mode_val}, skip=skip, limit=limit)


crud_sport = CRUDSport(Sport)
