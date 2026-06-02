from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_kinesis as kinesis,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_glue as glue,
    aws_athena as athena,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class DataPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Configuration
        self.project_name = "realtime-pipeline"
        self.stream_name = f"{self.project_name}-stream"
        self.bucket_name = f"{self.project_name}-data-lake-{self.account}"

        # Create S3 Data Lake
        self.data_lake_bucket = self._create_data_lake_bucket()

        # Create Kinesis Data Stream
        self.data_stream = self._create_kinesis_stream()

        # Create Dead Letter Queue
        self.dlq = self._create_dlq()

        # Create Lambda Processors
        self.stream_processor = self._create_stream_processor()
        self.batch_processor = self._create_batch_processor()

        # Create Glue Data Catalog
        self._create_glue_catalog()

        # Create Athena Workgroup
        self._create_athena_workgroup()

        # Create SNS Topic for alerts
        self.alert_topic = self._create_alert_topic()

        # Outputs
        CfnOutput(self, "StreamName", value=self.data_stream.stream_name)
        CfnOutput(self, "DataLakeBucket", value=self.data_lake_bucket.bucket_name)
        CfnOutput(self, "DLQName", value=self.dlq.queue_name)

    def _create_data_lake_bucket(self) -> s3.Bucket:
        """Create S3 bucket for data lake with lifecycle policies."""
        bucket = s3.Bucket(
            self,
            "DataLake",
            bucket_name=self.bucket_name,
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="TransitionToIA",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        )
                    ],
                ),
                s3.LifecycleRule(
                    id="TransitionToGlacier",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90),
                        )
                    ],
                ),
                s3.LifecycleRule(
                    id="ExpireOldData",
                    expiration=Duration.days(2555),  # ~7 years
                ),
            ],
        )
        return bucket

    def _create_kinesis_stream(self) -> kinesis.Stream:
        """Create Kinesis Data Stream with on-demand capacity."""
        stream = kinesis.Stream(
            self,
            "DataStream",
            stream_name=self.stream_name,
            stream_mode=kinesis.StreamMode.ON_DEMAND,
            retention_period=Duration.hours(24),
            encryption=kinesis.StreamEncryption.MANAGED,
        )
        return stream

    def _create_dlq(self) -> sqs.Queue:
        """Create Dead Letter Queue for failed records."""
        dlq = sqs.Queue(
            self,
            "DeadLetterQueue",
            queue_name=f"{self.project_name}-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(5),
        )
        return dlq

    def _create_stream_processor(self) -> lambda_.Function:
        """Create Lambda function for real-time stream processing."""
        function = lambda_.Function(
            self,
            "StreamProcessor",
            function_name=f"{self.project_name}-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="processor.handler",
            code=lambda_.Code.from_asset("src/processors"),
            timeout=Duration.minutes(2),
            memory_size=1024,
            reserved_concurrent_executions=100,
            environment={
                "DATA_LAKE_BUCKET": self.data_lake_bucket.bucket_name,
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "stream-processor",
            },
            dead_letter_queue=self.dlq,
            tracing=lambda_.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Grant permissions
        self.data_stream.grant_read(function)
        self.data_lake_bucket.grant_write(function)

        # Add Kinesis trigger
        function.add_event_source_mapping(
            "KinesisTrigger",
            event_source_arn=self.data_stream.stream_arn,
            starting_position=lambda_.StartingPosition.LATEST,
            batch_size=100,
            max_batching_window=Duration.seconds(5),
            retry_attempts=3,
            parallelization_factor=10,
        )

        return function

    def _create_batch_processor(self) -> lambda_.Function:
        """Create Lambda function for batch aggregation."""
        function = lambda_.Function(
            self,
            "BatchProcessor",
            function_name=f"{self.project_name}-batch",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="batch_processor.handler",
            code=lambda_.Code.from_asset("src/processors"),
            timeout=Duration.minutes(5),
            memory_size=2048,
            environment={
                "DATA_LAKE_BUCKET": self.data_lake_bucket.bucket_name,
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "batch-processor",
            },
            tracing=lambda_.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        self.data_lake_bucket.grant_read_write(function)

        return function

    def _create_glue_catalog(self) -> None:
        """Create Glue database and tables."""
        database = glue.CfnDatabase(
            self,
            "GlueDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=f"{self.project_name}_db",
                description="Database for real-time pipeline data",
            ),
        )

        # Raw events table
        glue.CfnTable(
            self,
            "RawEventsTable",
            catalog_id=self.account,
            database_name=database.ref,
            table_input=glue.CfnTable.TableInputProperty(
                name="raw_events",
                description="Raw events from Kinesis stream",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "classification": "parquet",
                    "compressionType": "snappy",
                },
                partition_keys=[
                    glue.CfnTable.ColumnProperty(name="year", type="string"),
                    glue.CfnTable.ColumnProperty(name="month", type="string"),
                    glue.CfnTable.ColumnProperty(name="day", type="string"),
                    glue.CfnTable.ColumnProperty(name="hour", type="string"),
                ],
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=[
                        glue.CfnTable.ColumnProperty(name="event_id", type="string"),
                        glue.CfnTable.ColumnProperty(name="event_type", type="string"),
                        glue.CfnTable.ColumnProperty(name="timestamp", type="timestamp"),
                        glue.CfnTable.ColumnProperty(name="user_id", type="string"),
                        glue.CfnTable.ColumnProperty(name="session_id", type="string"),
                        glue.CfnTable.ColumnProperty(name="properties", type="map<string,string>"),
                        glue.CfnTable.ColumnProperty(name="processed_at", type="timestamp"),
                    ],
                    location=f"s3://{self.bucket_name}/raw/",
                    input_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                    ),
                ),
            ),
        )

    def _create_athena_workgroup(self) -> None:
        """Create Athena workgroup for queries."""
        athena.CfnWorkGroup(
            self,
            "AnalyticsWorkgroup",
            name=f"{self.project_name}-analytics",
            description="Workgroup for pipeline analytics",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{self.bucket_name}/athena-results/",
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3",
                    ),
                ),
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics_enabled=True,
            ),
        )

    def _create_alert_topic(self) -> sns.Topic:
        """Create SNS topic for pipeline alerts."""
        topic = sns.Topic(
            self,
            "AlertTopic",
            topic_name=f"{self.project_name}-alerts",
            display_name="Data Pipeline Alerts",
        )
        return topic
