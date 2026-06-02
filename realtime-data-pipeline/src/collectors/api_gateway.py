"""
API Gateway Lambda integration for event ingestion.
Validates incoming events and puts them onto Kinesis Data Streams.
"""

import json
import os
from typing import Any, Dict

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

kinesis_client = boto3.client("kinesis")
STREAM_NAME = os.environ.get("STREAM_NAME", "realtime-pipeline-stream")

# Rate limiting (simple in-memory, use API Gateway throttling in production)
REQUEST_COUNT: Dict[str, int] = {}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    API Gateway Lambda proxy integration handler.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    http_method = event.get("httpMethod", "POST")
    path = event.get("path", "/")

    if http_method == "POST" and path == "/events":
        return ingest_event(event)
    elif http_method == "GET" and path == "/health":
        return health_check()
    else:
        return create_response(404, {"error": "Not found"})


def ingest_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest a single event into Kinesis."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return create_response(400, {"error": "Invalid JSON"})

    # Validate required fields
    if "event_type" not in body:
        return create_response(400, {"error": "Missing required field: event_type"})

    if "timestamp" not in body:
        body["timestamp"] = __import__("datetime").datetime.utcnow().isoformat()

    # Add metadata
    body["_ingested_at"] = __import__("datetime").datetime.utcnow().isoformat()
    body["_source_ip"] = event.get("requestContext", {}).get(
        "identity", {}
    ).get("sourceIp", "unknown")

    # Generate partition key for even distribution
    partition_key = body.get("user_id", body.get("session_id", "default"))

    try:
        response = kinesis_client.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(body),
            PartitionKey=partition_key,
        )

        logger.info(
            f"Event ingested",
            extra={
                "shard_id": response["ShardId"],
                "sequence_number": response["SequenceNumber"],
                "event_type": body["event_type"],
            },
        )

        return create_response(
            202,
            {
                "status": "accepted",
                "sequence_number": response["SequenceNumber"],
            },
        )

    except Exception as e:
        logger.error(f"Failed to ingest event: {e}")
        return create_response(500, {"error": "Failed to ingest event"})


def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    try:
        # Check Kinesis stream status
        kinesis_client.describe_stream_summary(StreamName=STREAM_NAME)
        return create_response(
            200,
            {
                "status": "healthy",
                "stream": STREAM_NAME,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return create_response(
            503,
            {
                "status": "unhealthy",
                "error": str(e),
            },
        )


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(body),
    }
