"""
Real-time stream processor for Kinesis Data Streams.
Processes events, validates schema, and writes to S3 as Parquet files.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

s3_client = boto3.client("s3")
BUCKET_NAME = os.environ["DATA_LAKE_BUCKET"]

# Schema for validation
EVENT_SCHEMA = {
    "required": ["event_type", "timestamp"],
    "optional": ["user_id", "session_id", "properties"],
}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Process Kinesis records batch.

    Args:
        event: Kinesis event containing records
        context: Lambda context

    Returns:
        Processing result with batch item failures
    """
    records = event.get("Records", [])
    logger.info(f"Processing {len(records)} records")

    valid_records: List[Dict[str, Any]] = []
    failed_records: List[Dict[str, str]] = []

    for record in records:
        try:
            # Decode Kinesis data
            payload = json.loads(
                record["kinesis"]["data"]
            )

            # Validate and transform
            processed = process_event(payload)
            if processed:
                valid_records.append(processed)
            else:
                failed_records.append({
                    "itemIdentifier": record["kinesis"]["sequenceNumber"]
                })

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in record: {e}")
            failed_records.append({
                "itemIdentifier": record["kinesis"]["sequenceNumber"]
            })
        except Exception as e:
            logger.error(f"Error processing record: {e}")
            failed_records.append({
                "itemIdentifier": record["kinesis"]["sequenceNumber"]
            })

    # Write valid records to S3
    if valid_records:
        write_to_s3(valid_records)

    logger.info(
        f"Processed {len(valid_records)} valid, {len(failed_records)} failed"
    )

    return {
        "batchItemFailures": failed_records
    }


def process_event(event: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Validate and enrich an event.

    Args:
        event: Raw event data

    Returns:
        Processed event or None if invalid
    """
    # Check required fields
    for field in EVENT_SCHEMA["required"]:
        if field not in event:
            logger.warning(f"Missing required field: {field}")
            return None

    # Validate timestamp
    try:
        timestamp = parse_timestamp(event["timestamp"])
    except (ValueError, TypeError):
        logger.warning(f"Invalid timestamp: {event.get('timestamp')}")
        return None

    # Enrich event
    processed = {
        "event_id": event.get("event_id", str(uuid.uuid4())),
        "event_type": event["event_type"],
        "timestamp": timestamp.isoformat(),
        "user_id": event.get("user_id", "anonymous"),
        "session_id": event.get("session_id", ""),
        "properties": json.dumps(event.get("properties", {})),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    return processed


def parse_timestamp(ts: Any) -> datetime:
    """Parse various timestamp formats."""
    if isinstance(ts, (int, float)):
        # Unix timestamp
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(ts, str):
        # ISO format
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    else:
        raise ValueError(f"Unsupported timestamp type: {type(ts)}")


def write_to_s3(records: List[Dict[str, Any]]) -> None:
    """
    Write records to S3 as Parquet file.

    Args:
        records: List of processed records
    """
    now = datetime.now(timezone.utc)

    # Create Parquet table
    table = pa.Table.from_pylist(records)

    # Write to buffer
    buffer = pa.BufferOutputStream()
    pq.write_table(
        table,
        buffer,
        compression="snappy",
        use_dictionary=True,
    )

    # S3 key with partitioning
    key = (
        f"raw/year={now.year}/"
        f"month={now.month:02d}/"
        f"day={now.day:02d}/"
        f"hour={now.hour:02d}/"
        f"events_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.parquet"
    )

    # Upload to S3
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=buffer.getvalue().to_pybytes(),
        ContentType="application/octet-stream",
    )

    logger.info(f"Wrote {len(records)} records to s3://{BUCKET_NAME}/{key}")
