#!/usr/bin/env python3
"""
Script to send test events to the Kinesis stream.
Usage: python send_test_events.py --count 100 --stream-name realtime-pipeline-stream
"""

import argparse
import json
import random
import time
import uuid
from datetime import datetime, timezone

import boto3

EVENT_TYPES = [
    "page_view",
    "click",
    "scroll",
    "product_view",
    "add_to_cart",
    "checkout_started",
    "purchase",
    "search",
    "filter_applied",
    "share",
]

PAGES = ["/", "/products", "/cart", "/checkout", "/about", "/contact"]

PRODUCTS = ["laptop", "phone", "headphones", "keyboard", "mouse", "monitor"]


def generate_event() -> dict:
    """Generate a random test event."""
    event_type = random.choice(EVENT_TYPES)
    user_id = f"user_{random.randint(1, 1000)}"
    session_id = f"sess_{random.randint(1, 500)}"

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session_id,
        "properties": {},
    }

    # Add event-specific properties
    if event_type == "page_view":
        event["properties"]["page"] = random.choice(PAGES)
        event["properties"]["referrer"] = random.choice(["google", "direct", "social"])
    elif event_type == "product_view":
        event["properties"]["product_id"] = random.choice(PRODUCTS)
        event["properties"]["price"] = round(random.uniform(10, 1000), 2)
    elif event_type == "purchase":
        event["properties"]["order_id"] = f"ORD-{random.randint(10000, 99999)}"
        event["properties"]["total"] = round(random.uniform(50, 500), 2)
        event["properties"]["items"] = random.randint(1, 5)
    elif event_type == "search":
        event["properties"]["query"] = random.choice(PRODUCTS)
        event["properties"]["results_count"] = random.randint(0, 50)

    return event


def send_events(stream_name: str, count: int, batch_size: int = 500) -> None:
    """Send events to Kinesis stream."""
    kinesis = boto3.client("kinesis")

    print(f"Sending {count} events to stream: {stream_name}")

    sent = 0
    while sent < count:
        batch = []
        for _ in range(min(batch_size, count - sent)):
            event = generate_event()
            batch.append({
                "Data": json.dumps(event),
                "PartitionKey": event["user_id"],
            })

        try:
            response = kinesis.put_records(
                StreamName=stream_name,
                Records=batch,
            )

            failed = response.get("FailedRecordCount", 0)
            successful = len(batch) - failed
            sent += successful

            print(f"Sent: {sent}/{count} (failed: {failed})")

            if failed > 0:
                print(f"Warning: {failed} records failed")

        except Exception as e:
            print(f"Error sending batch: {e}")
            time.sleep(1)

    print(f"Done! Sent {sent} events total.")


def main():
    parser = argparse.ArgumentParser(description="Send test events to Kinesis")
    parser.add_argument(
        "--stream-name",
        default="realtime-pipeline-stream",
        help="Kinesis stream name",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1000,
        help="Number of events to send",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Records per batch (max 500)",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=0,
        help="Events per second (0 = unlimited)",
    )

    args = parser.parse_args()

    if args.rate > 0:
        # Rate-limited sending
        delay = 1.0 / args.rate
        kinesis = boto3.client("kinesis")

        print(f"Sending {args.count} events at {args.rate}/sec")
        for i in range(args.count):
            event = generate_event()
            kinesis.put_record(
                StreamName=args.stream_name,
                Data=json.dumps(event),
                PartitionKey=event["user_id"],
            )
            if (i + 1) % 100 == 0:
                print(f"Sent: {i + 1}/{args.count}")
            time.sleep(delay)
    else:
        send_events(args.stream_name, args.count, args.batch_size)


if __name__ == "__main__":
    main()
