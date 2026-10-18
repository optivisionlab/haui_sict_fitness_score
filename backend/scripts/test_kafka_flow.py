import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

KAFKA_SERVER = "localhost:9092"
TOPIC_JOBS = "video-grading-jobs"
TOPIC_RESULTS = "video-grading-results"


async def run_kafka_test():
    print(f"[*] Testing connection to Kafka at {KAFKA_SERVER}...")

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_SERVER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    
    test_group = f"test-client-{uuid.uuid4().hex[:6]}"
    consumer = AIOKafkaConsumer(
        TOPIC_RESULTS,
        bootstrap_servers=KAFKA_SERVER,
        group_id=test_group,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
    )

    await producer.start()
    await consumer.start()
    print("[+] Successfully connected Producer and Consumer to Kafka!")

    mock_result_id = f"test_{uuid.uuid4().hex[:8]}"
    mock_job = {
        "jobId": mock_result_id,
        "resultId": mock_result_id,
        "taskId": "task_demo_1",
        "sportId": "sport_demo_pushup",
        "sportCode": "pushup",
        "userId": "user_demo_123",
        "videoUrl": "videos/pushup/test_demo.mp4",
        "minioEndpoint": "localhost:9000",
        "minioBucket": "videos",
        "attemptNo": 1,
        "priority": "normal",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }

    print(f"[📤] Publishing test job to topic '{TOPIC_JOBS}': resultId={mock_result_id}")
    await producer.send_and_wait(TOPIC_JOBS, value=mock_job, key=mock_result_id)
    print("[+] Job sent successfully! Waiting for AI Worker to process and publish result...")

    try:
        # Chờ kết quả từ AI worker trong vòng tối đa 20 giây
        async def wait_for_result():
            async for msg in consumer:
                payload = msg.value
                if payload.get("resultId") == mock_result_id:
                    return payload
            return None

        result = await asyncio.wait_for(wait_for_result(), timeout=20.0)
        print("\n🎉 [📥] Received result from AI Worker!")
        print(f"  - Result ID: {result.get('resultId')}")
        print(f"  - Status:    {result.get('status')}")
        print(f"  - AI Score:  {result.get('aiScore')}")
        print(f"  - AI Comment:{result.get('aiComment')}")
        print(f"  - Metrics:   {result.get('metrics')}")
        print(f"  - Processed: {result.get('processingTimeSec')}s")
        print("\n✅ End-to-end Kafka grading flow PASSED!")

    except asyncio.TimeoutError:
        print("\n⚠️ Timed out waiting for AI Worker result (Is the worker running?).")
    finally:
        await producer.stop()
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_kafka_test())
