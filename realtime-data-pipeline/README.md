# Real-time Data Pipeline

A production-grade real-time data processing pipeline built with AWS CDK, Kinesis, Lambda, S3, and Athena. Processes high-velocity event streams with sub-second latency, stores data in a data lake, and provides SQL analytics capabilities.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Sources   │────▶│   Kinesis    │────▶│   Lambda    │
│  (IoT/Web)  │     │   Data Stream│     │  Processor  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┘
                       │
              ┌────────▼────────┐
              │   S3 Data Lake  │
              │  (Parquet/Iceberg)│
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │     Athena      │
              │   (SQL Queries) │
              └─────────────────┘
```

## Tech Stack

- **AWS CDK** - Infrastructure as Code (Python)
- **Amazon Kinesis Data Streams** - Real-time data ingestion
- **AWS Lambda** - Stream processing (Python 3.11)
- **Amazon S3** - Data lake storage
- **AWS Glue** - Data catalog & ETL
- **Amazon Athena** - Serverless SQL analytics
- **Amazon CloudWatch** - Monitoring & alarms
- **Amazon SNS** - Alerting

## Features

- Real-time event ingestion (10,000+ events/sec)
- Stream processing with windowed aggregations
- Data lake with partitioned Parquet files
- Schema validation & data quality checks
- Dead letter queue for failed records
- Auto-scaling based on stream metrics
- Athena queries for business intelligence
- Comprehensive CloudWatch dashboards
- Cost-optimized with S3 lifecycle policies

## Getting Started

### Prerequisites

- AWS CLI configured
- AWS CDK installed (`npm install -g aws-cdk`)
- Python 3.11+
- Docker (for Lambda packaging)

### Deploy

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy stack
cdk deploy

# Run tests
pytest tests/ -v --cov=src --cov-report=html
```

## Data Flow

1. **Ingestion**: Events are sent to Kinesis Data Streams via API Gateway or direct SDK calls
2. **Processing**: Lambda functions process batches with windowed aggregations
3. **Storage**: Processed data lands in S3 as Parquet files partitioned by date/hour
4. **Analytics**: Athena queries the Glue Data Catalog for SQL-based analytics
5. **Monitoring**: CloudWatch tracks throughput, latency, and error rates

## Project Structure

```
.
├── src/
│   ├── collectors/      # Event collection endpoints
│   ├── processors/      # Lambda stream processors
│   ├── analytics/       # Athena queries & dashboards
│   └── utils/           # Shared utilities
├── infrastructure/      # CDK stacks
├── tests/               # Unit & integration tests
├── scripts/             # Helper scripts
└── cdk.json             # CDK configuration
```

## License

MIT
