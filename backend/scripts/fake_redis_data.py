import argparse
import random
import time
from datetime import datetime
import json
import sys
import redis


def create_user_hash(r: redis.Redis, user_id: int, camera_id: int, flags: dict):
    key = f"user:{user_id}:data"
    mapping = {}
    mapping.update({k: str(v) for k, v in flags.items()})
    mapping["last_cam"] = str(camera_id)
    mapping["start_time"] = datetime.utcnow().isoformat()
    r.hset(key, mapping=mapping)
    print(f"Created hash {key} -> camera={camera_id} flags={flags}")
    return key


def flip_flag(r: redis.Redis, user_id: int, flag_name: str):
    key = f"user:{user_id}:data"
    # This HSET should trigger a __keyevent@DB__:hset event when Redis notify is configured
    r.hset(key, flag_name, "1")
    print(f"Flipped {key} {flag_name}=1")

    # Optionally publish explicit notification to user channel as well to simulate direct notify
    try:
        evt = {
            "type": "checkin",
            "user_id": str(user_id),
            "camera": r.hget(key, "last_cam") or None,
            "flag": flag_name,
            "timestamp": datetime.utcnow().isoformat(),
            "key": key,
            "message": f"Test checkin for user {user_id} at {datetime.utcnow().isoformat()}"
        }
        r.publish(f"user:{user_id}:channel", json.dumps(evt, ensure_ascii=False))
        print(f"Published direct event to user:{user_id}:channel")
    except Exception:
        pass


def parse_args():
    p = argparse.ArgumentParser(description="Generate fake Redis checkin data and flip flags")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default=6379, type=int)
    p.add_argument("--db", default=0, type=int)
    p.add_argument("--count", type=int, default=5, help="How many user hashes to create when --user-ids not provided")
    p.add_argument("--user-ids", type=int, nargs="*", help="Specific user ids to create (overrides --count)")
    p.add_argument("--camera-ids", type=int, nargs="*", help="List of camera ids to choose from (default 1..5)")
    p.add_argument("--flags", type=int, default=2, help="Number of flag fields to create (flag1..flagN)")
    p.add_argument("--flip", type=int, default=1, help="How many flips (0->1) to perform after creation")
    p.add_argument("--delay", type=float, default=1.0, help="Seconds to wait before flipping flags")
    return p.parse_args()


def main():
    args = parse_args()
    r = redis.Redis(host=args.host, port=args.port, db=args.db, decode_responses=True)

    try:
        r.ping()
    except Exception as e:
        print("Failed to connect to Redis:", e, file=sys.stderr)
        sys.exit(2)

    if args.user_ids:
        user_ids = args.user_ids
    else:
        base = 100
        user_ids = list(range(base, base + args.count))

    camera_ids = args.camera_ids or list(range(1, 6))

    # create hashes with flags == "0"
    for uid in user_ids:
        cam = random.choice(camera_ids)
        flags = {f"flag{i+1}": 0 for i in range(args.flags)}
        create_user_hash(r, uid, cam, flags)

    print(f"Waiting {args.delay}s before flipping flags...")
    time.sleep(args.delay)

    # choose some users and flip one random flag to "1"
    flip_count = min(args.flip, len(user_ids))
    flip_users = random.sample(user_ids, flip_count)
    for uid in flip_users:
        flag_to_flip = f"flag{random.randint(1, args.flags)}"
        flip_flag(r, uid, flag_to_flip)

    print("Done.")


if __name__ == "__main__":
    main()
