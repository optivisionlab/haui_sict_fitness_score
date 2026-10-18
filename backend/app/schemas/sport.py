from datetime import datetime
from typing import Optional
from pydantic import Field

from app.models.base import PyObjectId
from app.models.sport import SportMode
from app.schemas.common import BaseSchema


class ScoringConfigSchema(BaseSchema):
    metrics_fields: list[str] = Field(default_factory=list)
    formula: Optional[str] = None
    thresholds: dict[str, float] = Field(default_factory=dict)


class SportBase(BaseSchema):
    code: str
    name: str
    mode: SportMode
    scoring_config: ScoringConfigSchema = Field(default_factory=ScoringConfigSchema)


class SportCreate(SportBase):
    pass


class SportUpdate(BaseSchema):
    code: Optional[str] = None
    name: Optional[str] = None
    mode: Optional[SportMode] = None
    scoring_config: Optional[ScoringConfigSchema] = None


class SportRead(BaseSchema):
    id: PyObjectId
    code: str
    name: str
    mode: SportMode
    scoring_config: ScoringConfigSchema
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
