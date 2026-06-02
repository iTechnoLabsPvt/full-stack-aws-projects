from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_logs as logs,
)
from constructs import Construct


class MonitoringStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.project_name = "realtime-pipeline"

        # Import resources from pipeline stack
        stream_name = f"{self.project_name}-stream"
        function_name = f"{self.project_name}-processor"

        # Create dashboard
        self._create_dashboard(stream_name, function_name)

        # Create alarms
        self._create_alarms(stream_name, function_name)

    def _create_dashboard(self, stream_name: str, function_name: str) -> None:
        """Create CloudWatch dashboard for pipeline monitoring."""
        dashboard = cloudwatch.Dashboard(
            self,
            "PipelineDashboard",
            dashboard_name=f"{self.project_name}-dashboard",
        )

        # Kinesis metrics
        incoming_records = cloudwatch.Metric(
            namespace="AWS/Kinesis",
            metric_name="IncomingRecords",
            dimensions_map={"StreamName": stream_name},
            statistic="Sum",
            period=Duration.minutes(1),
        )

        get_records_iterator_age = cloudwatch.Metric(
            namespace="AWS/Kinesis",
            metric_name="GetRecords.IteratorAgeMilliseconds",
            dimensions_map={"StreamName": stream_name},
            statistic="Average",
            period=Duration.minutes(1),
        )

        # Lambda metrics
        lambda_invocations = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Invocations",
            dimensions_map={"FunctionName": function_name},
            statistic="Sum",
            period=Duration.minutes(1),
        )

        lambda_errors = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Errors",
            dimensions_map={"FunctionName": function_name},
            statistic="Sum",
            period=Duration.minutes(1),
        )

        lambda_duration = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Duration",
            dimensions_map={"FunctionName": function_name},
            statistic="Average",
            period=Duration.minutes(1),
        )

        lambda_throttles = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Throttles",
            dimensions_map={"FunctionName": function_name},
            statistic="Sum",
            period=Duration.minutes(1),
        )

        dashboard.add_widgets(
            # Header
            cloudwatch.TextWidget(
                markdown=f"# {self.project_name} Pipeline Monitoring",
                width=24,
                height=1,
            ),
            # Kinesis metrics
            cloudwatch.GraphWidget(
                title="Incoming Records (per minute)",
                left=[incoming_records],
                width=12,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Iterator Age (ms)",
                left=[get_records_iterator_age],
                width=12,
                height=6,
            ),
            # Lambda metrics
            cloudwatch.GraphWidget(
                title="Lambda Invocations",
                left=[lambda_invocations],
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Lambda Errors",
                left=[lambda_errors],
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Lambda Duration (ms)",
                left=[lambda_duration],
                width=8,
                height=6,
            ),
            # Custom metrics
            cloudwatch.GraphWidget(
                title="Lambda Throttles",
                left=[lambda_throttles],
                width=12,
                height=6,
            ),
            cloudwatch.LogQueryWidget(
                title="Recent Errors",
                width=12,
                height=6,
                log_group_names=[f"/aws/lambda/{function_name}"],
                query_string="fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20",
            ),
        )

    def _create_alarms(self, stream_name: str, function_name: str) -> None:
        """Create CloudWatch alarms for critical metrics."""
        # High iterator age alarm
        iterator_age_alarm = cloudwatch.Alarm(
            self,
            "HighIteratorAgeAlarm",
            alarm_name=f"{self.project_name}-high-iterator-age",
            metric=cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="GetRecords.IteratorAgeMilliseconds",
                dimensions_map={"StreamName": stream_name},
                statistic="Average",
                period=Duration.minutes(1),
            ),
            threshold=30000,  # 30 seconds
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="Iterator age is high - processing is falling behind",
        )

        # Lambda error rate alarm
        error_alarm = cloudwatch.Alarm(
            self,
            "LambdaErrorAlarm",
            alarm_name=f"{self.project_name}-lambda-errors",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": function_name},
                statistic="Sum",
                period=Duration.minutes(1),
            ),
            threshold=10,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="Lambda function is experiencing errors",
        )

        # Lambda duration alarm
        duration_alarm = cloudwatch.Alarm(
            self,
            "LambdaDurationAlarm",
            alarm_name=f"{self.project_name}-lambda-duration",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Duration",
                dimensions_map={"FunctionName": function_name},
                statistic="p99",
                period=Duration.minutes(1),
            ),
            threshold=100000,  # 100 seconds
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="Lambda function duration is high",
        )

        # Throttling alarm
        throttle_alarm = cloudwatch.Alarm(
            self,
            "LambdaThrottleAlarm",
            alarm_name=f"{self.project_name}-lambda-throttles",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Throttles",
                dimensions_map={"FunctionName": function_name},
                statistic="Sum",
                period=Duration.minutes(1),
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="Lambda function is being throttled",
        )
