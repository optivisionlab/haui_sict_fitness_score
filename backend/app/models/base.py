from datetime import datetime, timezone
from typing import Annotated, Any, ClassVar, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from pydantic.alias_generators import to_camel


def validate_object_id(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError(f"Invalid ObjectId: {v!r}")


PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]


class EmbeddedModel(BaseModel):
    """Base model cho các object nhúng bên trong document."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        arbitrary_types_allowed=True,
        from_attributes=True,
    )


class BaseDocument(BaseModel):
    """Base model cho document trong collection."""

    __collection__: ClassVar[str] = ""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        arbitrary_types_allowed=True,
        from_attributes=True,
    )

    def to_mongo(self, exclude_none: bool = False) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=exclude_none)
