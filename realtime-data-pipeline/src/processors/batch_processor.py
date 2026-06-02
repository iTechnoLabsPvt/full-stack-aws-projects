"""
Batch processor for hourly aggregations and data quality checks.
Triggered by CloudWatch Events schedule.
"""

import json
import os
from datetime import datetime, timedelta, timezone
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


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Process hourly batch aggregations.

    Args:
        event: CloudWatch Events trigger
        context: Lambda context

    Returns:
        Processing summary
    """
    # Process previous hour
    process_hour = datetime.now(timezone.utc) - timedelta(hours=1)

    logger.info(f"Processing aggregations for hour: {process_hour.isoformat()}")

    # Read raw data
    prefix = (
        f"raw/year={process_hour.year}/"
        f"month={process_hour.month:02d}/"
        f"day={process_hour.day:02d}/"
        f"hour={process_hour.hour:02d}/"
    )

    records = read_parquet_files(prefix)

    if not records:
        logger.info("No records found for processing")
        return {"status": "no_data", "records_processed": 0}

    # Generate aggregations
    aggregations = generate_aggregations(records, process_hour)

    # Write aggregations
    write_aggregations(aggregations, process_hour)

    # Data quality check
    quality_report = run_quality_checks(records)
    write_quality_report(quality_report, process_hour)

    logger.info(f"Processed {len(records)} records")

    return {
        "status": "success",
        "records_processed": len(records),
        "hour": process_hour.isoformat(),
    }


def read_parquet_files(prefix: str) -> List[Dict[str, Any]]:
    """Read all Parquet files under a prefix."""
    records = []

    response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=prefix,
    )

    for obj in response.get("Contents", []):
        try:
            result = s3_client.get_object(
                Bucket=BUCKET_NAME,
                Key=obj["Key"],
            )
            table = pq.read_table(result["Body"])
            records.extend(table.to_pylist())
        except Exception as e:
            logger.error(f"Error reading {obj['Key']}: {e}")

    return records


def generate_aggregations(
    records: List[Dict[str, Any]], hour: datetime
) -> List[Dict[str, Any]]:
    """Generate hourly aggregations."""
    from collections import defaultdict

    # Event type counts
    event_counts = defaultdict(int)
    user_counts = set()
    session_counts = set()

    for record in records:
        event_counts[record["event_type"]] += 1
        user_counts.add(record.get("user_id", "anonymous"))
        session_counts.add(record.get("session_id", ""))

    aggregations = []
    for event_type, count in event_counts.items():
        aggregations.append({
            "hour": hour.isoformat(),
            "event_type": event_type,
            "event_count": count,
            "unique_users": len(user_counts),
            "unique_sessions": len(session_counts),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        })

    return aggregations


def write_aggregations(
    aggregations: List[Dict[str, Any]], hour: datetime
) -> None:
    """Write aggregation results to S3."""
    table = pa.Table.from_pylist(aggregations)

    buffer = pa.BufferOutputStream()
    pq.write_table(table, buffer, compression="snappy")

    key = (
        f"aggregated/year={hour.year}/"
        f"month={hour.month:02d}/"
        f"day={hour.day:02d}/"
        f"hour={hour.hour:02d}/"
        f"aggregations.parquet"
    )

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=buffer.getvalue().to_pybytes(),
    )

    logger.info(f"Wrote aggregations to s3://{BUCKET_NAME}/{key}")


def run_quality_checks(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run data quality checks."""
    total = len(records)

    checks = {
        "total_records": total,
        "missing_event_type": sum(1 for r in records if not r.get("event_type")),
        "missing_user_id": sum(1 for r in records if not r.get("user_id")),
        "missing_timestamp": sum(1 for r in records if not r.get("timestamp")),
        "unique_event_types": len(set(r.get("event_type", "") for r in records)),
        "timestamp_range": {
            "min": min(r.get("timestamp", "") for r in records) if records else None,
            "max": max(r.get("timestamp", "") for r in records) if records else None,
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    return checks


def write_quality_report(
    report: Dict[str, Any], hour: datetime
) -> None:
    """Write quality report to S3."""
    key = (
        f"quality/year={hour.year}/"
        f"month={hour.month:02d}/"
        f"day={hour.day:02d}/"
        f"hour={hour.hour:02d}/"
        f"report.json"
    )

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(report, indent=2).encode(),
        ContentType="application/json",
    )

    logger.info(f"Wrote quality report to s3://{BUCKET_NAME}/{key}")
