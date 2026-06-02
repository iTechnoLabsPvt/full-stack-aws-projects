#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.pipeline_stack import DataPipelineStack
from stacks.monitoring_stack import MonitoringStack

app = cdk.App()

environment = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
)

# Main data pipeline stack
DataPipelineStack(
    app,
    "RealtimeDataPipeline",
    env=environment,
    description="Real-time data processing pipeline with Kinesis, Lambda, and S3",
)

# Monitoring stack
MonitoringStack(
    app,
    "PipelineMonitoring",
    env=environment,
    description="CloudWatch dashboards and alarms for the data pipeline",
)

app.synth()
