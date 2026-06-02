"""
Custom metrics publishing utilities.
"""

import os
from typing import Dict, Any

import boto3

cloudwatch = boto3.client("cloudwatch")
NAMESPACE = os.environ.get("METRICS_NAMESPACE", "DataPipeline")


def put_metric(
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: Dict[str, str] = None,
) -> None:
    """Publish a custom metric to CloudWatch."""
    metric_data = {
        "MetricName": metric_name,
        "Value": value,
        "Unit": unit,
    }

    if dimensions:
        metric_data["Dimensions"] = [
            {"Name": k, "Value": v} for k, v in dimensions.items()
        ]

    cloudwatch.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[metric_data],
    )


def put_metric_count(metric_name: str, count: int = 1, **dimensions: str) -> None:
    """Publish a count metric."""
    put_metric(metric_name, float(count), "Count", dimensions or None)


def put_metric_duration(metric_name: str, duration_ms: float, **dimensions: str) -> None:
    """Publish a duration metric in milliseconds."""
    put_metric(metric_name, duration_ms, "Milliseconds", dimensions or None)


def put_metric_size(metric_name: str, size_bytes: float, **dimensions: str) -> None:
    """Publish a size metric in bytes."""
    put_metric(metric_name, size_bytes, "Bytes", dimensions or None)
