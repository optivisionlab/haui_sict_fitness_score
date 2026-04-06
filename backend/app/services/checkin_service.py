"""Check-in persistence and user display name lookup.

Extracted from redis_events to break the circular dependency between
redis_dispatcher and the endpoint module.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.core.database import engine
from app.models.camera import Camera, CameraUserClass
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_user_display_name(user_id: str) -> Optional[str]:
    """Fetch user's full name or username via a thread-pooled sync query."""
    try:
        uid = int(user_id) if user_id and str(user_id).isdigit() else None
        if uid is None:
            return None

        def _sync_fetch() -> Optional[str]:
            with Session(engine) as session:
                user = session.exec(select(User).where(User.user_id == uid)).one_or_none()
                if not user:
                    return None
                return user.full_name or user.user_name or str(user.user_id)

        return await asyncio.to_thread(_sync_fetch)
    except Exception:
        logger.exception("Failed to fetch user display name for %s", user_id)
        return None


async def save_checkin_to_db(
    user_id: str,
    camera_id: Optional[str],
    flag_name: str,
    timestamp: str,
    *,
    image_url: Optional[str] = None,
    lap: Optional[str] = None,
    avg_speed: Optional[str] = None,
    exam_id: Optional[str] = None,
    class_id: Optional[str] = None,
) -> None:
    """Persist a check-in record with optional telemetry and media reference."""
    try:
        uid = int(user_id) if user_id and str(user_id).isdigit() else None
        cam_id = int(camera_id) if camera_id and str(camera_id).isdigit() else None
        ex_id = int(exam_id) if exam_id and str(exam_id).isdigit() else None
        cls_id = int(class_id) if class_id and str(class_id).isdigit() else None

        checkin_dt: Optional[datetime] = None
        try:
            if isinstance(timestamp, str):
                checkin_dt = datetime.fromisoformat(timestamp)
            elif isinstance(timestamp, datetime):
                checkin_dt = timestamp
        except Exception:
            checkin_dt = datetime.utcnow()

        def _sync_save() -> None:
            with Session(engine) as session:
                if uid is None or cam_id is None:
                    return

                existing_cam = session.get(Camera, cam_id)
                if existing_cam is None:
                    cam = Camera(camera_id=cam_id, camera_name=f"Camera {cam_id}")
                    session.add(cam)
                    session.commit()

                lap_val: Optional[int] = None
                try:
                    if lap is not None:
                        lap_val = int(lap)
                except (TypeError, ValueError):
                    lap_val = None

                avg_speed_val: Optional[float] = None
                try:
                    if avg_speed is not None:
                        avg_speed_val = float(avg_speed)
                except (TypeError, ValueError):
                    avg_speed_val = None

                record = CameraUserClass(
                    user_id=uid,
                    camera_id=cam_id,
                    class_id=cls_id,
                    exam_id=ex_id,
                    lap=lap_val if lap_val is not None else 1,
                    avg_speed=avg_speed_val,
                    flag=flag_name,
                    checkin_time=checkin_dt,
                    image_url=image_url,
                )
                session.add(record)
                session.commit()

        await asyncio.to_thread(_sync_save)
    except Exception as exc:
        logger.exception("Failed to save checkin to DB: %s", exc)
