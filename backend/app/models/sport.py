from enum import Enum
from typing import ClassVar, Optional

from pydantic import Field

from .base import BaseDocument, EmbeddedModel


class SportMode(str, Enum):
    VIDEO = "video"
    CAMERA = "camera"


class ScoringConfig(EmbeddedModel):
    metrics_fields: list[str] = Field(default_factory=list)
    formula: Optional[str] = None
    thresholds: dict[str, float] = Field(default_factory=dict)


class Sport(BaseDocument):
    __collection__: ClassVar[str] = "sports"

    code: str
    name: str
    mode: SportMode
    scoring_config: ScoringConfig = Field(default_factory=ScoringConfig)
