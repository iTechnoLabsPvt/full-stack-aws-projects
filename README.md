# Full-Stack & AWS Deployment Portfolio

A collection of three production-ready projects demonstrating expertise in serverless architecture, containerized full-stack applications, and real-time data pipelines on AWS.

---

## Projects Overview

| # | Project | Stack | AWS Services | IaC |
|---|---------|-------|--------------|-----|
| 1 | **Serverless E-commerce API** | Node.js, TypeScript | Lambda, API Gateway, DynamoDB, Cognito, SQS, X-Ray | AWS SAM |
| 2 | **Full-Stack Task Manager** | React, Node.js/Express, PostgreSQL | ECS Fargate, RDS, ElastiCache, ALB, CloudFront | Terraform |
| 3 | **Real-time Data Pipeline** | Python 3.11 | Kinesis, Lambda, S3, Glue, Athena, CloudWatch | AWS CDK |

---

## Project 1: Serverless E-commerce API

**Repository:** `serverless-ecommerce-api`

A production-ready serverless backend for an e-commerce platform handling product catalog, order management, and payment webhooks.

### Key Features
- Single-table DynamoDB design with GSIs for efficient queries
- JWT authentication via Cognito User Pools
- Event-driven order processing with SQS
- Comprehensive input validation with Joi
- Structured logging with AWS Lambda Powertools
- 85%+ test coverage with Jest

### Architecture
```
Client → API Gateway → Lambda → DynamoDB (Single-Table)
                          ↓
                        SQS → Lambda (Order Processing)
```

### Deploy
```bash
cd serverless-ecommerce-api
npm install
sam build
sam deploy --guided
```

---

## Project 2: Full-Stack Task Manager

**Repository:** `fullstack-task-manager`

A modern task management SaaS application with real-time collaboration, deployed on AWS ECS Fargate with full Terraform infrastructure.

### Key Features
- React 18 SPA with TypeScript, Tailwind CSS, and React Query
- Express API with Prisma ORM, JWT auth, and Redis caching
- Role-based access control (Admin/Manager/Member)
- Kanban board with drag-and-drop task management
- Auto-scaling ECS Fargate with ALB
- Multi-environment Terraform modules (VPC, ECS, RDS, ALB)

### Architecture
```
React (S3/CloudFront) → ALB → ECS Fargate (Node.js)
                              → RDS PostgreSQL
                              → ElastiCache Redis
```

### Deploy
```bash
cd fullstack-task-manager
# Local
docker-compose up -d

# AWS
cd infrastructure/environments/dev
terraform init
terraform apply
```

---

## Project 3: Real-time Data Pipeline

**Repository:** `realtime-data-pipeline`

A high-throughput event processing pipeline handling 10,000+ events/second with sub-second latency.

### Key Features
- Kinesis Data Streams with on-demand capacity
- Lambda stream processors with batch item failures
- S3 data lake with Parquet/Snappy compression
- Glue Data Catalog with partitioned tables
- Athena SQL analytics with pre-built queries
- CloudWatch dashboards and alarms
- Data quality checks and reporting

### Architecture
```
Sources → Kinesis → Lambda → S3 (Parquet partitions)
                              → Glue Catalog
                              → Athena (SQL queries)
```

### Deploy
```bash
cd realtime-data-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

---

## CI/CD

All projects include GitHub Actions workflows for:
- Automated testing (unit + integration)
- Linting and code quality checks
- Infrastructure validation
- Staged deployments (dev → staging → production)

---

## Contact

- **GitHub:** [github.com/iTechnoLabsPvt](https://github.com/iTechnoLabsPvt)
- **Email:** business@itechnolabs.biz
- **Availability:** Immediate start
- **Communication:** Async-first (Slack, Email), sync when needed (Zoom, Teams)
