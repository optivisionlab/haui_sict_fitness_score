from typing import AsyncGenerator
import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Request, Body
from fastapi.responses import StreamingResponse
from app.core.database import get_async_redis

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/events/global")
async def global_events(request: Request):
	"""SSE endpoint streaming notifications for all users (non-personalized).

	Subscribes to the global Redis channel "__global_redis_events__" and forwards
	incoming messages as SSE events. Known types ("checkin", "flag_update") are
	emitted as named events; other payloads are sent as default data events.
	"""
	return StreamingResponse(
		_async_global_sse_generator(request),
		media_type="text/event-stream",
	)


@router.post("/notify/global")
async def notify_global(payload: dict = Body(...)):
	"""Publish a notification to the global Redis channel.

	Example body: {"message": "System notice", "type": "checkin"}
	"""
	redis = get_async_redis()
	try:
		payload.setdefault("timestamp", datetime.utcnow().isoformat())
		await redis.publish("__global_redis_events__", json.dumps(payload, ensure_ascii=False))
		return {"status": "sent"}
	except Exception:
		logger.exception("Failed to publish to global channel")
		return {"status": "error"}


async def _async_global_sse_generator(request: Request) -> AsyncGenerator[str, None]:
	"""Generator that streams all global events via SSE.

	Listens on Redis channel "__global_redis_events__" and yields:
	- event: checkin       data: {message, payload}
	- event: flag_update   data: {message, payload}
	- default              data: {message, payload}
	"""
	redis_client = get_async_redis()
	pubsub = redis_client.pubsub()

	await pubsub.subscribe("__global_redis_events__")

	try:
		while True:
			if await request.is_disconnected():
				break

			message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
			if message:
				data = message.get("data")
				if isinstance(data, bytes):
					try:
						data = data.decode()
					except Exception:
						data = None
				if not data:
					await asyncio.sleep(0.01)
					continue

				try:
					payload_obj = json.loads(data)
				except Exception:
					payload_obj = None

				if not payload_obj or not isinstance(payload_obj, dict):
					await asyncio.sleep(0.01)
					continue

				evt_type = payload_obj.get("type")
				message_text = payload_obj.get("message")
				if not message_text and "data" in payload_obj:
					message_text = payload_obj["data"]

				serialized = json.dumps({"message": message_text, "payload": payload_obj}, ensure_ascii=False)

				if evt_type == "checkin":
					yield f"event: checkin\ndata: {serialized}\n\n"
				elif evt_type == "flag_update":
					yield f"event: flag_update\ndata: {serialized}\n\n"
				else:
					yield f"data: {serialized}\n\n"

			# cooperative sleep
			await asyncio.sleep(0.01)
	finally:
		try:
			await pubsub.unsubscribe()
			await pubsub.close()
		except Exception:
			pass

