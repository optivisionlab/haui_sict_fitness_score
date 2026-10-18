from typing import Optional
from fastapi import HTTPException, status

from app.crud.sport import crud_sport
from app.models.sport import Sport, SportMode
from app.schemas.sport import SportCreate, SportUpdate


class SportService:
    def create_sport(self, sport_in: SportCreate) -> Sport:
        """Tạo môn thể thao mới."""
        existing = crud_sport.get_by_code(sport_in.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Môn thể thao với mã code '{sport_in.code}' đã tồn tại",
            )
        return crud_sport.create(sport_in)

    def get_by_id(self, sport_id: str) -> Sport:
        """Lấy chi tiết môn thể thao."""
        sport = crud_sport.get(sport_id)
        if not sport:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy môn thể thao",
            )
        return sport

    def get_by_code(self, code: str) -> Sport:
        """Lấy môn thể thao theo mã code."""
        sport = crud_sport.get_by_code(code)
        if not sport:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy môn thể thao mã '{code}'",
            )
        return sport

    def list_sports(
        self,
        mode: Optional[SportMode] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Sport], int]:
        """Lấy danh sách các môn thể thao."""
        if mode:
            return crud_sport.get_by_mode(mode, skip=skip, limit=limit)
        return crud_sport.get_multi(skip=skip, limit=limit)

    def update_sport(self, sport_id: str, sport_in: SportUpdate) -> Sport:
        """Cập nhật thông tin môn thể thao."""
        self.get_by_id(sport_id)
        if sport_in.code:
            existing = crud_sport.get_by_code(sport_in.code)
            if existing and str(existing.id) != str(sport_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mã code '{sport_in.code}' đã thuộc về môn khác",
                )
        updated = crud_sport.update(sport_id, sport_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cập nhật môn thể thao thất bại",
            )
        return updated

    def delete_sport(self, sport_id: str) -> bool:
        """Xóa môn thể thao."""
        self.get_by_id(sport_id)
        return crud_sport.delete(sport_id)

    def get_definitions(self) -> list[dict]:
        """Lấy danh sách đặc tả chi tiết (metrics, formula, thresholds) của tất cả các môn thể thao."""
        from app.services.sports.definitions import list_sport_definitions
        return [d.to_dict() for d in list_sport_definitions()]

    def sync_sports_from_definitions(self) -> list[Sport]:
        """
        Tự động đồng bộ các môn thể thao từ SPORT_DEFINITIONS vào cơ sở dữ liệu MongoDB
        nếu chưa tồn tại trong database.
        """
        from app.schemas.sport import ScoringConfigSchema, SportCreate
        from app.services.sports.definitions import SPORT_DEFINITIONS

        synced: list[Sport] = []
        for def_item in SPORT_DEFINITIONS.values():
            fuzzy_code = "PICKLE" if "PICKLE" in def_item.code else ("RUN" if "RUN" in def_item.code else def_item.code)
            existing = crud_sport.collection.find_one({
                "$or": [
                    {"code": def_item.code},
                    {"code": def_item.code.lower()},
                    {"code": def_item.code.upper()},
                    {"code": fuzzy_code},
                ]
            })
            if not existing:
                create_data = SportCreate(
                    code=def_item.code.upper(),
                    name=def_item.name,
                    mode=def_item.mode,
                    scoring_config=ScoringConfigSchema(
                        metrics_fields=[m.name for m in def_item.metrics],
                        formula=def_item.formula_description,
                        thresholds=def_item.thresholds,
                    ),
                )
                created = crud_sport.create(create_data)
                synced.append(created)
        return synced


sport_service = SportService()
